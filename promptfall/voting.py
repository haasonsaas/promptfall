"""Voting UI components for Promptfall."""

from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label
from textual.screen import Screen
from textual.reactive import reactive
from typing import List, Dict, Any


class VotingScreen(Screen):
    """Screen for voting on player responses."""
    
    votes_cast = reactive(0)
    time_remaining = reactive(20)
    
    def __init__(self, responses: List[Dict], voting_callback, back_callback):
        super().__init__()
        self.responses = responses
        self.voting_callback = voting_callback
        self.back_callback = back_callback
        self.voted_for = None
        
    def compose(self):
        """Create voting UI components."""
        yield Container(
            Vertical(
                Static("🗳️ Vote for the Best Response!", id="voting-title"),
                Static(f"Time remaining: {self.time_remaining}s", id="voting-timer"),
                Container(id="responses-container"),
                Horizontal(
                    Button("Skip Vote", id="skip-vote", variant="warning"),
                    Button("← Back", id="back-to-game", variant="error"),
                    id="voting-actions"
                ),
                id="voting-content"
            ),
            id="voting-main"
        )
        
    def on_mount(self):
        """Called when screen is mounted."""
        self.populate_responses()
        
    def populate_responses(self):
        """Populate the responses for voting."""
        container = self.query_one("#responses-container")
        
        for i, response_data in enumerate(self.responses):
            player_name = response_data.get("player_name", "Unknown")
            response_text = response_data.get("response", "")
            player_id = response_data.get("player_id")
            
            # Create response card
            response_card = Container(
                Vertical(
                    Static(f"Response by {player_name}", classes="response-author"),
                    Static(f'"{response_text}"', classes="response-text"),
                    Button(
                        f"Vote for {player_name}", 
                        id=f"vote-{player_id}",
                        variant="primary",
                        classes="vote-button"
                    ),
                    classes="response-card"
                ),
                id=f"response-{i}",
                classes="response-container"
            )
            
            container.mount(response_card)
            
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "back-to-game":
            self.back_callback()
            
        elif button_id == "skip-vote":
            self.app.pop_screen()
            
        elif button_id.startswith("vote-"):
            target_player_id = button_id.replace("vote-", "")
            self.cast_vote(target_player_id)
            
    def cast_vote(self, player_id: str):
        """Cast a vote for a player."""
        if self.voted_for is None:
            self.voted_for = player_id
            self.voting_callback(player_id)
            
            # Update UI to show vote cast
            vote_button = self.query_one(f"#vote-{player_id}")
            vote_button.label = "✓ Voted!"
            vote_button.disabled = True
            vote_button.variant = "success"
            
            # Disable all other vote buttons
            for response_data in self.responses:
                other_player_id = response_data.get("player_id")
                if other_player_id != player_id:
                    try:
                        other_button = self.query_one(f"#vote-{other_player_id}")
                        other_button.disabled = True
                    except:
                        pass
                        
    def update_timer(self, time_left: int):
        """Update the voting timer."""
        self.time_remaining = time_left
        timer_widget = self.query_one("#voting-timer")
        timer_widget.update(f"Time remaining: {time_left}s")
        
        if time_left <= 0:
            self.app.pop_screen()


class ResultsScreen(Screen):
    """Screen for showing round results."""
    
    def __init__(self, results: List[Dict], next_round_callback, back_callback):
        super().__init__()
        self.results = results
        self.next_round_callback = next_round_callback
        self.back_callback = back_callback
        
    def compose(self):
        """Create results UI components."""
        yield Container(
            Vertical(
                Static("🏆 Round Results!", id="results-title"),
                Container(id="results-container"),
                Horizontal(
                    Button("Next Round", id="next-round", variant="primary"),
                    Button("← Back to Lobby", id="back-to-lobby", variant="warning"),
                    id="results-actions"
                ),
                id="results-content"
            ),
            id="results-main"
        )
        
    def on_mount(self):
        """Called when screen is mounted."""
        self.populate_results()
        
    def populate_results(self):
        """Populate the results display."""
        container = self.query_one("#results-container")
        
        for i, result in enumerate(self.results):
            player_name = result.get("player_name", "Unknown")
            response = result.get("response", "")
            score = result.get("score", 0)
            
            # Determine ranking
            if i == 0:
                rank_icon = "🥇"
                rank_text = "1st Place"
            elif i == 1:
                rank_icon = "🥈" 
                rank_text = "2nd Place"
            elif i == 2:
                rank_icon = "🥉"
                rank_text = "3rd Place"
            else:
                rank_icon = f"{i+1}."
                rank_text = f"{i+1}th Place"
                
            result_card = Container(
                Vertical(
                    Static(f"{rank_icon} {rank_text} - {player_name}", classes="result-rank"),
                    Static(f"Score: {score} points", classes="result-score"),
                    Static(f'Response: "{response}"', classes="result-response"),
                    classes="result-card"
                ),
                id=f"result-{i}",
                classes="result-container"
            )
            
            container.mount(result_card)
            
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events."""
        if event.button.id == "next-round":
            self.next_round_callback()
            
        elif event.button.id == "back-to-lobby":
            self.back_callback()