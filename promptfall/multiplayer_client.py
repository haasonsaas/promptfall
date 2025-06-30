"""WebSocket client for multiplayer communication."""

import asyncio
import json
import websockets
from typing import Optional, Callable, Dict, Any


class MultiplayerClient:
    """WebSocket client for connecting to multiplayer server."""
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.player_id: Optional[str] = None
        self.room_id: Optional[str] = None
        self.message_handlers: Dict[str, Callable] = {}
        self.connected = False
        
    def on_message(self, message_type: str, handler: Callable):
        """Register a message handler for specific message types."""
        self.message_handlers[message_type] = handler
        
    async def connect(self, host="localhost", port=8765):
        """Connect to the multiplayer server."""
        try:
            uri = f"ws://{host}:{port}"
            self.websocket = await websockets.connect(uri)
            self.connected = True
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from the server."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            
    async def send_message(self, message: dict):
        """Send a message to the server."""
        if self.websocket and self.connected:
            try:
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                print(f"Failed to send message: {e}")
                self.connected = False
                
    async def _listen_for_messages(self):
        """Listen for incoming messages from the server."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                message_type = data.get("type")
                
                # Handle connection confirmation
                if message_type == "connected":
                    self.player_id = data.get("player_id")
                    
                # Call registered handler if exists
                if message_type in self.message_handlers:
                    await self.message_handlers[message_type](data)
                    
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
        except Exception as e:
            print(f"Error listening for messages: {e}")
            self.connected = False
            
    async def create_room(self, room_name: str):
        """Create a new game room."""
        await self.send_message({
            "type": "create_room",
            "room_name": room_name
        })
        
    async def join_room(self, room_id: str, player_name: str):
        """Join an existing room."""
        await self.send_message({
            "type": "join_room",
            "room_id": room_id,
            "player_name": player_name
        })
        
    async def leave_room(self):
        """Leave current room."""
        if self.room_id:
            await self.send_message({
                "type": "leave_room",
                "room_id": self.room_id
            })
            self.room_id = None
            
    async def start_game(self):
        """Start the game in current room."""
        if self.room_id:
            await self.send_message({
                "type": "start_game",
                "room_id": self.room_id
            })
            
    async def submit_response(self, response: str):
        """Submit response for current round."""
        if self.room_id:
            await self.send_message({
                "type": "submit_response",
                "room_id": self.room_id,
                "response": response
            })
            
    async def cast_vote(self, target_player_id: str):
        """Vote for another player's response."""
        if self.room_id:
            await self.send_message({
                "type": "cast_vote",
                "room_id": self.room_id,
                "target_id": target_player_id
            })
            
    async def get_room_list(self):
        """Request list of available rooms."""
        await self.send_message({
            "type": "get_rooms"
        })