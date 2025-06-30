"""WebSocket server for multiplayer Promptfall."""

import asyncio
import json
import uuid
import websockets
from typing import Dict, List, Set
from dataclasses import dataclass, asdict
from .game import GameEngine, Player, Challenge


@dataclass
class Room:
    """Game room data structure."""
    id: str
    name: str
    players: List[Player]
    game_engine: GameEngine
    max_players: int = 4
    is_active: bool = False
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "players": [{"id": p.id, "name": p.name, "score": p.score} for p in self.players],
            "player_count": len(self.players),
            "max_players": self.max_players,
            "is_active": self.is_active
        }


class MultiplayerServer:
    """WebSocket server for handling multiplayer games."""
    
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.player_to_room: Dict[str, str] = {}
        
    async def register(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new client connection."""
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket
        return connection_id
        
    async def unregister(self, connection_id: str):
        """Unregister a client connection."""
        if connection_id in self.connections:
            # Remove player from room if they were in one
            if connection_id in self.player_to_room:
                room_id = self.player_to_room[connection_id]
                await self.leave_room(connection_id, room_id)
            
            del self.connections[connection_id]
            
    async def send_to_player(self, player_id: str, message: dict):
        """Send message to a specific player."""
        if player_id in self.connections:
            websocket = self.connections[player_id]
            try:
                await websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                await self.unregister(player_id)
                
    async def broadcast_to_room(self, room_id: str, message: dict, exclude_player: str = None):
        """Broadcast message to all players in a room."""
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        for player in room.players:
            if player.id != exclude_player:
                await self.send_to_player(player.id, message)
                
    async def create_room(self, player_id: str, room_name: str) -> str:
        """Create a new game room."""
        room_id = str(uuid.uuid4())
        game_engine = GameEngine()
        
        room = Room(
            id=room_id,
            name=room_name,
            players=[],
            game_engine=game_engine
        )
        
        self.rooms[room_id] = room
        await self.join_room(player_id, room_id, "Host")
        
        return room_id
        
    async def join_room(self, player_id: str, room_id: str, player_name: str):
        """Add player to a room."""
        if room_id not in self.rooms:
            await self.send_to_player(player_id, {
                "type": "error",
                "message": "Room not found"
            })
            return False
            
        room = self.rooms[room_id]
        
        if len(room.players) >= room.max_players:
            await self.send_to_player(player_id, {
                "type": "error",
                "message": "Room is full"
            })
            return False
            
        # Remove player from previous room if any
        if player_id in self.player_to_room:
            old_room_id = self.player_to_room[player_id]
            await self.leave_room(player_id, old_room_id)
            
        # Add player to room
        player = room.game_engine.add_player(player_id, player_name)
        self.player_to_room[player_id] = room_id
        
        # Notify all players in room
        await self.broadcast_to_room(room_id, {
            "type": "player_joined",
            "player": {"id": player.id, "name": player.name},
            "room": room.to_dict()
        })
        
        # Send room info to new player
        await self.send_to_player(player_id, {
            "type": "room_joined",
            "room": room.to_dict()
        })
        
        return True
        
    async def leave_room(self, player_id: str, room_id: str):
        """Remove player from room."""
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        
        # Remove player from room
        room.players = [p for p in room.players if p.id != player_id]
        
        if player_id in self.player_to_room:
            del self.player_to_room[player_id]
            
        # Notify remaining players
        await self.broadcast_to_room(room_id, {
            "type": "player_left",
            "player_id": player_id,
            "room": room.to_dict()
        })
        
        # Delete room if empty
        if not room.players:
            del self.rooms[room_id]
            
    async def start_game(self, player_id: str, room_id: str):
        """Start a multiplayer game."""
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        
        if len(room.players) < 2:
            await self.send_to_player(player_id, {
                "type": "error",
                "message": "Need at least 2 players to start"
            })
            return
            
        # Start the game
        challenge = room.game_engine.start_round()
        room.is_active = True
        
        # Broadcast game start to all players
        await self.broadcast_to_room(room_id, {
            "type": "game_started",
            "challenge": {
                "prompt": challenge.prompt,
                "category": challenge.category,
                "time_limit": challenge.time_limit
            },
            "room": room.to_dict()
        })
        
        # Start timer
        asyncio.create_task(self.game_timer(room_id, challenge.time_limit))
        
    async def game_timer(self, room_id: str, duration: int):
        """Handle game timer countdown."""
        for remaining in range(duration, 0, -1):
            await asyncio.sleep(1)
            
            if room_id not in self.rooms or not self.rooms[room_id].is_active:
                return
                
            await self.broadcast_to_room(room_id, {
                "type": "timer_update",
                "time_remaining": remaining
            })
            
        # Time's up - move to voting phase
        await self.start_voting_phase(room_id)
        
    async def submit_response(self, player_id: str, room_id: str, response: str):
        """Submit player response."""
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        success = room.game_engine.submit_response(player_id, response)
        
        if success:
            # Notify other players that this player submitted
            await self.broadcast_to_room(room_id, {
                "type": "response_submitted",
                "player_id": player_id
            }, exclude_player=player_id)
            
            # Check if all players have submitted
            submitted_count = sum(1 for p in room.players if p.response_generated)
            if submitted_count == len(room.players):
                await self.start_voting_phase(room_id)
                
    async def start_voting_phase(self, room_id: str):
        """Start the voting phase."""
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        
        # Collect all responses
        responses = []
        for player in room.players:
            if player.current_response:
                responses.append({
                    "player_id": player.id,
                    "player_name": player.name,
                    "response": player.current_response
                })
                
        # Broadcast voting phase start
        await self.broadcast_to_room(room_id, {
            "type": "voting_started",
            "responses": responses,
            "voting_time": 20
        })
        
        # Start voting timer
        asyncio.create_task(self.voting_timer(room_id, 20))
        
    async def voting_timer(self, room_id: str, duration: int):
        """Handle voting timer countdown."""
        for remaining in range(duration, 0, -1):
            await asyncio.sleep(1)
            
            if room_id not in self.rooms:
                return
                
            await self.broadcast_to_room(room_id, {
                "type": "voting_timer_update",
                "time_remaining": remaining
            })
            
        # Voting time's up - show results
        await self.end_round(room_id)
        
    async def cast_vote(self, voter_id: str, room_id: str, target_id: str):
        """Cast a vote for another player's response."""
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        success = room.game_engine.vote_for_response(voter_id, target_id)
        
        if success:
            await self.send_to_player(voter_id, {
                "type": "vote_cast",
                "target_id": target_id
            })
            
    async def end_round(self, room_id: str):
        """End the current round and show results."""
        if room_id not in self.rooms:
            return
            
        room = self.rooms[room_id]
        room.is_active = False
        
        # Calculate results
        results = []
        for player in room.players:
            results.append({
                "player_id": player.id,
                "player_name": player.name,
                "response": player.current_response,
                "score": player.score
            })
            
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Broadcast results
        await self.broadcast_to_room(room_id, {
            "type": "round_ended",
            "results": results,
            "room": room.to_dict()
        })
        
    async def get_room_list(self, player_id: str):
        """Get list of available rooms."""
        room_list = []
        for room in self.rooms.values():
            if not room.is_active and len(room.players) < room.max_players:
                room_list.append(room.to_dict())
                
        await self.send_to_player(player_id, {
            "type": "room_list",
            "rooms": room_list
        })
        
    async def handle_message(self, connection_id: str, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "create_room":
                room_id = await self.create_room(connection_id, data.get("room_name", "New Room"))
                
            elif message_type == "join_room":
                await self.join_room(connection_id, data.get("room_id"), data.get("player_name", "Player"))
                
            elif message_type == "leave_room":
                await self.leave_room(connection_id, data.get("room_id"))
                
            elif message_type == "start_game":
                await self.start_game(connection_id, data.get("room_id"))
                
            elif message_type == "submit_response":
                await self.submit_response(connection_id, data.get("room_id"), data.get("response"))
                
            elif message_type == "cast_vote":
                await self.cast_vote(connection_id, data.get("room_id"), data.get("target_id"))
                
            elif message_type == "get_rooms":
                await self.get_room_list(connection_id)
                
        except json.JSONDecodeError:
            await self.send_to_player(connection_id, {
                "type": "error",
                "message": "Invalid message format"
            })
        except Exception as e:
            await self.send_to_player(connection_id, {
                "type": "error", 
                "message": str(e)
            })


# Global server instance
server = MultiplayerServer()


async def handle_client(websocket, path):
    """Handle new WebSocket client connection."""
    connection_id = await server.register(websocket)
    
    try:
        await server.send_to_player(connection_id, {
            "type": "connected",
            "player_id": connection_id
        })
        
        async for message in websocket:
            await server.handle_message(connection_id, message)
            
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        await server.unregister(connection_id)


def start_server(host="localhost", port=8765):
    """Start the WebSocket server."""
    print(f"Starting Promptfall multiplayer server on {host}:{port}")
    return websockets.serve(handle_client, host, port)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_server())
    asyncio.get_event_loop().run_forever()