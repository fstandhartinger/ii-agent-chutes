"""
Handles API routes related to user sessions and events.
"""
import logging
import time
import json
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import asc, text, and_, func

from ii_agent.db.manager import DatabaseManager
from ii_agent.db.models import Session, Event # Ensure direct import for clarity
from .common import create_cors_response # Relative import

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/sessions/{device_id}")
async def get_sessions_by_device_id(device_id: str):
    """Get all sessions for a specific device ID, sorted by creation time descending.
    For each session, also includes the first user message if available.
    """
    try:
        start_time = time.time()
        db_manager = DatabaseManager()

        with db_manager.get_session() as db_sess: # Renamed to db_sess to avoid conflict
            sessions_query = db_sess.query(Session).filter(
                Session.device_id == device_id
            ).order_by(Session.created_at.desc()).limit(50)
            
            sessions_list = sessions_query.all()
            
            sessions_data = []
            for sess_model in sessions_list: # Renamed to sess_model
                session_item = { # Renamed to session_item
                    "id": sess_model.id,
                    "workspace_dir": sess_model.workspace_dir,
                    "created_at": sess_model.created_at.isoformat() if sess_model.created_at else None,
                    "device_id": sess_model.device_id,
                    "summary": sess_model.summary,
                    "first_message": "",
                }
                sessions_data.append(session_item)
            
            if sessions_data:
                session_ids = [s["id"] for s in sessions_data]
                first_messages_map = {}

                try:
                    # ORM approach
                    subquery = db_sess.query(
                        Event.session_id,
                        func.min(Event.timestamp).label('min_timestamp')
                    ).filter(
                        Event.session_id.in_(session_ids),
                        Event.event_type == 'user_message'
                    ).group_by(Event.session_id).subquery()
                    
                    first_messages_results = db_sess.query(Event).join(
                        subquery,
                        and_(
                            Event.session_id == subquery.c.session_id,
                            Event.timestamp == subquery.c.min_timestamp,
                            Event.event_type == 'user_message' # Ensure we only get user_message type
                        )
                    ).all()
                    
                    for event in first_messages_results:
                        try:
                            payload = json.loads(event.event_payload) if event.event_payload else {}
                            first_message_text = payload.get("content", {}).get("text", "")
                            first_messages_map[event.session_id] = first_message_text
                        except json.JSONDecodeError:
                            logger.warning(f"Could not parse event_payload for event {event.id}")
                            first_messages_map[event.session_id] = "" # Default to empty if payload is malformed
                        except Exception as e_payload:
                            logger.error(f"Unexpected error processing payload for event {event.id}: {e_payload}")
                            first_messages_map[event.session_id] = ""


                    logger.info(f"ORM approach: Retrieved first messages for {len(first_messages_map)} sessions.")

                except Exception as e_orm:
                    logger.warning(f"ORM approach for first messages failed: {e_orm}, trying raw SQL.")
                    try:
                        # Raw SQL approach
                        params = {f'param_{i}': sid for i, sid in enumerate(session_ids)}
                        placeholders = ','.join([f':param_{i}' for i in range(len(session_ids))])
                        
                        # Corrected SQL to fetch the event_payload of the first 'user_message'
                        # This query ensures we get the payload associated with the MIN(timestamp)
                        first_messages_query_sql = text(f"""
                        WITH RankedMessages AS (
                            SELECT
                                session_id,
                                event_payload,
                                ROW_NUMBER() OVER(PARTITION BY session_id ORDER BY timestamp ASC) as rn
                            FROM event
                            WHERE session_id IN ({placeholders})
                            AND event_type = 'user_message'
                        )
                        SELECT session_id, event_payload
                        FROM RankedMessages
                        WHERE rn = 1;
                        """)
                        
                        result = db_sess.execute(first_messages_query_sql, params)
                        
                        for row in result:
                            try:
                                payload = json.loads(row.event_payload) if row.event_payload else {}
                                first_message_text = payload.get("content", {}).get("text", "")
                                first_messages_map[row.session_id] = first_message_text
                            except json.JSONDecodeError:
                                logger.warning(f"Raw SQL: Could not parse event_payload for session {row.session_id}")
                                first_messages_map[row.session_id] = ""
                            except Exception as e_payload_sql:
                                logger.error(f"Raw SQL: Unexpected error processing payload for session {row.session_id}: {e_payload_sql}")
                                first_messages_map[row.session_id] = ""
                        logger.info(f"Raw SQL approach: Retrieved first messages for {len(first_messages_map)} sessions.")

                    except Exception as e_sql:
                        logger.warning(f"Raw SQL approach for first messages failed: {e_sql}, falling back to individual queries.")
                        # Fallback: Individual queries (less efficient)
                        for sess_item in sessions_data[:10]: # Limit fallback to avoid excessive queries
                            try:
                                first_event = db_sess.query(Event).filter(
                                    Event.session_id == sess_item["id"],
                                    Event.event_type == 'user_message'
                                ).order_by(Event.timestamp.asc()).first()
                                if first_event and first_event.event_payload:
                                    payload = json.loads(first_event.event_payload)
                                    first_messages_map[sess_item["id"]] = payload.get("content", {}).get("text", "")
                                else:
                                    first_messages_map[sess_item["id"]] = ""
                            except Exception as e_fallback:
                                logger.error(f"Fallback: Error getting first message for session {sess_item['id']}: {e_fallback}")
                                first_messages_map[sess_item["id"]] = ""
                        logger.info(f"Fallback approach: Retrieved first messages for {len(first_messages_map)} sessions (limited).")
                
                for sess_item in sessions_data:
                    sess_item["first_message"] = first_messages_map.get(sess_item["id"], "")
            
            query_time = time.time() - start_time
            logger.info(f"get_sessions_by_device_id for {device_id} completed in {query_time:.3f}s. Found {len(sessions_data)} sessions.")
            return create_cors_response({"sessions": sessions_data})

    except Exception as e:
        logger.error(f"Error retrieving sessions for device {device_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving sessions: {str(e)}"
        )

@router.post("/api/sessions/{session_id}/summary")
async def update_session_summary(session_id: str, request: Request):
    """Update the summary for a specific session."""
    try:
        data = await request.json()
        summary = data.get("summary")

        if not summary:
            logger.error("Update Summary API: Summary is required")
            return create_cors_response({"error": "Summary is required"}, 400)

        db_manager = DatabaseManager()
        with db_manager.get_session() as db_sess:
            session = db_sess.query(Session).filter(Session.id == session_id).first()

            if not session:
                logger.error(f"Update Summary API: Session not found: {session_id}")
                return create_cors_response({"error": "Session not found"}, 404)

            session.summary = summary
            db_sess.commit()

            logger.info(f"Updated summary for session {session_id}")
            return create_cors_response({"message": "Summary updated successfully"})

    except Exception as e:
        logger.error(f"Error updating summary for session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error updating summary: {str(e)}"
        )

@router.get("/api/sessions/{session_id}/events")
async def get_session_events(session_id: str):
    """Get all events for a specific session ID, sorted by timestamp ascending."""
    try:
        start_time = time.time()
        db_manager = DatabaseManager()

        with db_manager.get_session() as db_sess: # Renamed to db_sess
            total_count = db_sess.query(Event).filter(Event.session_id == session_id).count()
            logger.info(f"Session {session_id} has {total_count} total events.")
            
            events_query = (
                db_sess.query(Event)
                .filter(Event.session_id == session_id)
                .order_by(asc(Event.timestamp))
                .limit(1000) # Keep limit for performance
                .all()
            )

            event_list = []
            for e_model in events_query: # Renamed to e_model
                event_list.append({
                    "id": e_model.id,
                    "session_id": e_model.session_id,
                    "timestamp": e_model.timestamp.isoformat(),
                    "event_type": e_model.event_type,
                    "event_payload": e_model.event_payload,
                    # Access related session safely
                    "workspace_dir": e_model.session.workspace_dir if e_model.session else None,
                })

            query_time = time.time() - start_time
            logger.info(f"get_session_events for {session_id} completed in {query_time:.3f}s. Returned {len(event_list)} of {total_count} events.")
            return create_cors_response({"events": event_list, "total_count": total_count, "returned_count": len(event_list)})

    except Exception as e:
        logger.error(f"Error retrieving events for session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving events: {str(e)}"
        )
