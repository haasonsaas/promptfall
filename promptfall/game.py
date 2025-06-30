"""Game logic and AI integration for Promptfall."""

import asyncio
import os
import random
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import openai

load_dotenv()

@dataclass
class Player:
    """Player data structure."""
    id: str
    name: str
    score: int = 0
    current_response: str = ""
    response_generated: bool = False

@dataclass
class Challenge:
    """Prompt challenge data structure."""
    prompt: str
    category: str
    time_limit: int = 30

class GameEngine:
    """Core game engine for Promptfall."""
    
    def __init__(self):
        self.players: List[Player] = []
        self.current_challenge: Optional[Challenge] = None
        self.round_active: bool = False
        self.time_remaining: int = 0
        self.openai_client = None
        
        # Initialize OpenAI client if API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "your_openai_api_key_here":
            openai.api_key = api_key
            self.openai_client = openai.OpenAI(api_key=api_key)
    
    def add_player(self, player_id: str, name: str) -> Player:
        """Add a new player to the game."""
        player = Player(id=player_id, name=name)
        self.players.append(player)
        return player
    
    def get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID."""
        return next((p for p in self.players if p.id == player_id), None)
    
    def generate_challenge(self) -> Challenge:
        """Generate a new prompt challenge."""
        challenges = [
            Challenge("Write a creative story about a robot learning to love", "Creative", 45),
            Challenge("Explain quantum physics using only food metaphors", "Educational", 30),
            Challenge("Create a product pitch for an impossible invention", "Business", 35),
            Challenge("Write a poem about debugging code at 3 AM", "Programming", 25),
            Challenge("Describe your morning routine as an epic fantasy adventure", "Humor", 30),
            Challenge("Explain social media to a medieval knight", "Historical", 35),
            Challenge("Write a motivational speech for vegetables", "Comedy", 25),
            Challenge("Create a conspiracy theory about why socks disappear", "Creative", 30),
            Challenge("Describe a day in the life of your phone's battery", "Perspective", 35),
            Challenge("Write assembly instructions for making friends", "Social", 30),
        ]
        
        challenge = random.choice(challenges)
        self.current_challenge = challenge
        return challenge
    
    def start_round(self) -> Challenge:
        """Start a new round with a fresh challenge."""
        challenge = self.generate_challenge()
        self.round_active = True
        self.time_remaining = challenge.time_limit
        
        # Reset player states
        for player in self.players:
            player.current_response = ""
            player.response_generated = False
        
        return challenge
    
    async def generate_ai_response(self, prompt: str, challenge: str) -> str:
        """Generate AI response using OpenAI API or fallback."""
        if not self.openai_client:
            return self._fallback_response(prompt, challenge)
        
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are participating in a creative prompt game. The challenge is: {challenge}. Write a creative, engaging response in 2-3 sentences."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.8
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._fallback_response(prompt, challenge)
    
    def _fallback_response(self, prompt: str, challenge: str) -> str:
        """Fallback response when API is unavailable."""
        fallback_responses = [
            "In a world where creativity meets technology, the impossible becomes possible through the power of imagination.",
            "Like a symphony of ideas dancing in digital harmony, this concept transforms the ordinary into extraordinary.",
            "Through the lens of innovation, we discover that every challenge is merely an opportunity wearing a clever disguise.",
            "In the grand theater of possibility, even the most mundane topics can steal the spotlight with the right perspective.",
            "Where logic meets whimsy, brilliant solutions emerge from the beautiful chaos of human creativity.",
        ]
        return random.choice(fallback_responses)
    
    def submit_response(self, player_id: str, response: str) -> bool:
        """Submit a player's response."""
        player = self.get_player(player_id)
        if not player or not self.round_active:
            return False
        
        player.current_response = response
        player.response_generated = True
        return True
    
    def end_round(self) -> List[Player]:
        """End the current round and return results."""
        self.round_active = False
        self.time_remaining = 0
        return self.players.copy()
    
    def vote_for_response(self, voter_id: str, target_id: str) -> bool:
        """Vote for another player's response."""
        voter = self.get_player(voter_id)
        target = self.get_player(target_id)
        
        if not voter or not target or voter_id == target_id:
            return False
        
        target.score += 1
        return True