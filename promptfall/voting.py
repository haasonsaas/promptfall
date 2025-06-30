"""Voting UI components for Promptfall."""

from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Label, Header, Footer
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
        yield Header()
        with Container(id="voting-main"):
            with Vertical(id="voting-content"):
                yield Static("🗳️ Vote for the Best Response!", id="voting-title")
                yield Static(f"Time remaining: {self.time_remaining}s", id="voting-timer")
                yield Container(id="responses-container")
                with Horizontal(id="voting-actions"):
                    yield Button("Skip Vote", id="skip-vote", variant="warning")
                    yield Button("← Back", id="back-to-game", variant="error")
        yield Footer()
        
    def on_mount(self):
        """Called when screen is mounted."""
        self.populate_responses()
        
    def populate_responses(self):
        """Populate the responses for voting."""
        container = self.query_one("#responses-container")
        
        # Debug info
        debug_info = Static(f"Debug: Found {len(self.responses)} responses", classes="debug-info")
        container.mount(debug_info)
        
        if not self.responses:
            container.mount(Static("No responses to vote on!", classes="no-responses"))
            return
            
        for i, response_data in enumerate(self.responses):
            player_name = response_data.get("player_name", "Unknown")
            response_text = response_data.get("response", "No response provided")
            player_id = response_data.get("player_id", f"player_{i}")
            
            # Truncate very long responses
            if len(response_text) > 200:
                response_text = response_text[:197] + "..."
            
            # Create response card
            response_container = Container(classes="response-container")
            response_card = Vertical(classes="response-card")
            
            # Add content to card
            response_card.mount(Static(f"Response by {player_name}", classes="response-author"))
            response_card.mount(Static(f'"{response_text}"', classes="response-text"))
            response_card.mount(Button(
                f"Vote for {player_name}", 
                id=f"vote-{player_id}",
                variant="primary",
                classes="vote-button"
            ))
            
            # Mount card to container and container to main container
            response_container.mount(response_card)
            container.mount(response_container)
            
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
        yield Header()
        with Container(id="results-main"):
            with Vertical(id="results-content"):
                yield Static("🏆 Round Results!", id="results-title")
                yield Container(id="results-container")
                with Horizontal(id="results-actions"):
                    yield Button("Next Round", id="next-round", variant="primary")
                    yield Button("← Back to Lobby", id="back-to-lobby", variant="warning")
        yield Footer()
        
    def on_mount(self):
        """Called when screen is mounted."""
        self.populate_results()
        
    def populate_results(self):
        """Populate the results display."""
        container = self.query_one("#results-container")
        
        if not self.results:
            container.mount(Static("No results to display!", classes="no-results"))
            return
        
        for i, result in enumerate(self.results):
            player_name = result.get("player_name", "Unknown")
            response = result.get("response", "No response")
            score = result.get("score", 0)
            
            # Truncate very long responses
            if len(response) > 150:
                response = response[:147] + "..."
            
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
                
            # Create result card
            result_container = Container(classes="result-container")
            result_card = Vertical(classes="result-card")
            
            # Add content to card
            result_card.mount(Static(f"{rank_icon} {rank_text} - {player_name}", classes="result-rank"))
            result_card.mount(Static(f"Score: {score} points", classes="result-score"))
            result_card.mount(Static(f'Response: "{response}"', classes="result-response"))
            
            # Mount card to container and container to main container
            result_container.mount(result_card)
            container.mount(result_container)
            
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events."""
        if event.button.id == "next-round":
            self.next_round_callback()
            
        elif event.button.id == "back-to-lobby":
            self.back_callback()