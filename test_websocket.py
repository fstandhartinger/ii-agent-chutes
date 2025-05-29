import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8001/ws?device_id=test&use_chutes=true&model_id=deepseek-ai/DeepSeek-R1-0528"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket connection established!")
            
            # Test sending a ping
            ping_message = {
                "type": "ping",
                "content": {}
            }
            await websocket.send(json.dumps(ping_message))
            print("Ping sent")
            
            # Wait for response
            response = await websocket.recv()
            print(f"Received: {response}")
            
    except Exception as e:
        print(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket()) 