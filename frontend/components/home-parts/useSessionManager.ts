import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Cookies from 'js-cookie';
import { v4 as uuidv4 } from 'uuid';
import { toast } from 'sonner';
import { AgentEvent, type IEvent } from '@/typings/agent'; // Corrected import for AgentEvent

export interface SessionManagerState {
  deviceId: string;
  sessionId: string | null;
  isLoadingSession: boolean;
  workspaceInfo: string;
  returnedFromChat: boolean;
  useNativeToolCalling: boolean;
}

export interface SessionManagerActions {
  setDeviceId: React.Dispatch<React.SetStateAction<string>>;
  setSessionId: React.Dispatch<React.SetStateAction<string | null>>;
  setIsLoadingSession: React.Dispatch<React.SetStateAction<boolean>>;
  setWorkspaceInfo: React.Dispatch<React.SetStateAction<string>>;
  setReturnedFromChat: React.Dispatch<React.SetStateAction<boolean>>;
  setUseNativeToolCalling: React.Dispatch<React.SetStateAction<boolean>>;
  resetSessionForNewChat: () => void; // Renamed from resetChat for clarity
  fetchSessionEvents: (
    id: string,
    onEventProcessed: (eventPayload: Record<string, unknown>, eventId: string) => void,
    onWorkspaceInfoLoaded: (path: string) => void,
    onLoadingComplete: () => void
  ) => Promise<void>;
}

export type UseSessionManagerReturn = SessionManagerState & SessionManagerActions;

const initialSessionManagerState: SessionManagerState = {
  deviceId: "",
  sessionId: null,
  isLoadingSession: false,
  workspaceInfo: "",
  returnedFromChat: false,
  useNativeToolCalling: false, // Default to false
};

export const useSessionManager = (
  initialState?: Partial<SessionManagerState>
): UseSessionManagerReturn => {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [deviceId, setDeviceId] = useState<string>(initialState?.deviceId || initialSessionManagerState.deviceId);
  const [sessionId, setSessionId] = useState<string | null>(initialState?.sessionId || initialSessionManagerState.sessionId);
  const [isLoadingSession, setIsLoadingSession] = useState<boolean>(initialState?.isLoadingSession || initialSessionManagerState.isLoadingSession);
  const [workspaceInfo, setWorkspaceInfo] = useState<string>(initialState?.workspaceInfo || initialSessionManagerState.workspaceInfo);
  const [returnedFromChat, setReturnedFromChat] = useState<boolean>(initialState?.returnedFromChat || initialSessionManagerState.returnedFromChat);
  const [useNativeToolCalling, setUseNativeToolCalling] = useState<boolean>(initialState?.useNativeToolCalling || initialSessionManagerState.useNativeToolCalling);

  // Initialize device ID from cookies
  useEffect(() => {
    let existingDeviceId = Cookies.get("device_id");
    if (!existingDeviceId) {
      existingDeviceId = uuidv4();
      Cookies.set("device_id", existingDeviceId, {
        expires: 365,
        sameSite: "strict",
        secure: typeof window !== 'undefined' && window.location.protocol === "https:",
      });
      console.log("Generated new device ID:", existingDeviceId);
    } else {
      console.log("Using existing device ID:", existingDeviceId);
    }
    setDeviceId(existingDeviceId);
  }, []);

  // Initialize session ID from URL search params - only for replay mode
  useEffect(() => {
    const idFromParams = searchParams.get('id');
    if (idFromParams) {
      // Only set sessionId if we're in replay mode (URL has id parameter)
      console.log("SESSION_MANAGER: Setting sessionId from URL params (replay mode):", idFromParams);
      setSessionId(idFromParams);
    } else {
      // If no id in URL, ensure sessionId is null (for fresh start)
      setSessionId(null);
    }
  }, [searchParams]);

  const resetSessionForNewChat = useCallback(() => {
    // This function is primarily for resetting client-side session state for a new chat,
    // not for closing WebSockets, which should be handled by useWebSocketManager.
    setSessionId(null);
    setWorkspaceInfo(""); // Reset workspace info for new session
    setReturnedFromChat(true); // Indicate user is starting fresh after a session
    router.push("/"); // Navigate to home, clearing URL params
  }, [router]);

  const fetchSessionEvents = useCallback(async (
    id: string,
    onEventProcessed: (eventPayload: Record<string, unknown>, eventId: string) => void,
    onWorkspaceInfoLoaded: (path: string) => void,
    onLoadingComplete: () => void
  ) => {
    if (!id) {
      console.warn("SESSION_MANAGER: Cannot fetch events - no session ID provided");
      onLoadingComplete();
      return;
    }

    console.log("SESSION_MANAGER: Fetching session events for ID:", id);
    setIsLoadingSession(true);
    
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/sessions/${id}/events`
      );

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("Session not found");
        } else if (response.status >= 500) {
          throw new Error("Server error - please try again later");
        } else {
          throw new Error(`Error fetching session events: ${response.statusText}`);
        }
      }

      const data = await response.json();
      
      if (!data.events || !Array.isArray(data.events)) {
        throw new Error("Invalid session data format");
      }

      // Extract workspace info if available from the first event or a specific event
      const firstEventWorkspaceDir = data.events?.[0]?.workspace_dir;
      if (firstEventWorkspaceDir) {
        console.log("SESSION_MANAGER: Setting workspace info from first event:", firstEventWorkspaceDir);
        onWorkspaceInfoLoaded(firstEventWorkspaceDir);
      }
      
      // Also check for specific workspace info event
      const workspaceEvent = data.events?.find(
        (e: IEvent) => e.event_type === AgentEvent.WORKSPACE_INFO
      );
      if (workspaceEvent?.event_payload?.path) {
        console.log("SESSION_MANAGER: Setting workspace info from WORKSPACE_INFO event:", workspaceEvent.event_payload.path);
        onWorkspaceInfoLoaded(workspaceEvent.event_payload.path as string);
      }

      // Process events with minimal delay for smoother UI updates
      console.log(`SESSION_MANAGER: Processing ${data.events.length} events`);
      for (let i = 0; i < data.events.length; i++) {
        const event = data.events[i];
        // Process each event with a small delay for smoother UI update
        await new Promise((resolve) => setTimeout(resolve, 20)); // Reduced delay for faster loading
        try {
          onEventProcessed({ ...event.event_payload, id: event.id }, event.id);
        } catch (eventError) {
          console.error(`SESSION_MANAGER: Error processing event ${i + 1}:`, eventError);
          // Continue processing other events even if one fails
        }
      }
      
      console.log("SESSION_MANAGER: Successfully loaded session history");
    } catch (error) {
      console.error("SESSION_MANAGER: Failed to fetch session events:", error);
      
      // Show appropriate error message based on error type
      if (error instanceof Error) {
        if (error.message.includes("Session not found")) {
          toast.error("Session not found - it may have been deleted or expired");
        } else if (error.message.includes("Server error")) {
          toast.error("Server error loading session - please try again later");
        } else {
          toast.error(`Failed to load session: ${error.message}`);
        }
      } else {
        toast.error("Failed to load session history - please try again");
      }
    } finally {
      setIsLoadingSession(false);
      onLoadingComplete();
    }
  }, []);

  return {
    deviceId,
    sessionId,
    isLoadingSession,
    workspaceInfo,
    returnedFromChat,
    useNativeToolCalling,
    setDeviceId,
    setSessionId,
    setIsLoadingSession,
    setWorkspaceInfo,
    setReturnedFromChat,
    setUseNativeToolCalling,
    resetSessionForNewChat,
    fetchSessionEvents,
  };
};
