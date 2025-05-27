import asyncio
import json
from typing import List

from websocket import WebSocket

# list of websockets instance
websocket_connections: List[WebSocket] = []

# send msg to websockets client (async)
async def broadcast_to_websockets(message: dict):
    """Send a message to all connected WebSocket clients"""
    if websocket_connections:
        disconnected = []
        for websocket in websocket_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except:
                disconnected.append(websocket)

        # Remove disconnected clients
        for ws in disconnected:
            websocket_connections.remove(ws)

# send msg to websocksts client (sync way)
def sync_broadcast_to_websockets(message: dict):
    """Synchronous wrapper for broadcasting to websockets from non-async context"""
    try:
        asyncio.run(broadcast_to_websockets(message))
    except Exception as e:
        print(f"Error broadcasting to websockets: {e}")
