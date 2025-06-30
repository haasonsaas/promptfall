"""Main entry point for Promptfall."""

import asyncio
from textual.app import App
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Button, Static, Input, TextArea, Label, ProgressBar
from textual.screen import Screen
from textual.reactive import reactive
from textual import work

from .game import GameEngine, Player, Challenge


class MenuScreen(Screen):
    """Main menu screen."""

    def compose(self):
        """Create child widgets for the app."""
        yield Header()
        with Container(id="main"):
            with Vertical(id="menu"):
                yield Static("⚔️ PROMPTFALL", id="title")
                yield Static("Tetris Attack meets Cards Against Humanity meets GPT", id="subtitle")
                yield Button("Single Player", id="single", variant="primary")
                yield Button("Multiplayer", id="multi", variant="success")
                yield Button("Quit", id="quit", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "quit":
            self.app.exit()
        elif event.button.id == "single":
            self.app.push_screen("game")
        elif event.button.id == "multi":
            self.app.push_screen("multiplayer")


class GameScreen(Screen):
    """Single player game screen."""
    
    game_state = reactive("menu")  # menu, playing, generating, results
    time_remaining = reactive(30)
    current_prompt = reactive("")
    
    def __init__(self):
        super().__init__()
        self.game_engine = GameEngine()
        self.player_id = "player1"
        self.player = self.game_engine.add_player(self.player_id, "You")
        self.current_challenge = None
        self.user_input = ""

    def compose(self):
        """Create child widgets for the game."""
        yield Header()
        with Container(id="game-container"):
            with Vertical(id="game-content"):
                yield Static("🎮 Single Player Mode", id="game-title")
                
                # Game state display
                with Container(id="challenge-area"):
                    yield Static("Click 'Start Round' to begin!", id="challenge-text")
                    yield ProgressBar(total=30, show_eta=False, id="timer-bar")
                
                # Input area
                with Container(id="input-area"):
                    yield TextArea(id="response-input")
                    
                # Action buttons
                with Horizontal(id="action-buttons"):
                    yield Button("Start Round", id="start-round", variant="primary")
                    yield Button("Generate AI Response", id="generate-ai", variant="success", disabled=True)
                    yield Button("Submit Response", id="submit", variant="warning", disabled=True)
                    yield Button("← Back to Menu", id="back", variant="error")
                
                # Results area
                with ScrollableContainer(id="results-area"):
                    yield Static("", id="results-text")
                    
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "start-round":
            self.start_new_round()
        elif event.button.id == "generate-ai":
            self.generate_ai_response()
        elif event.button.id == "submit":
            self.submit_response()
    
    def start_new_round(self):
        """Start a new game round."""
        self.current_challenge = self.game_engine.start_round()
        self.game_state = "playing"
        self.time_remaining = self.current_challenge.time_limit
        
        # Update UI
        challenge_text = self.query_one("#challenge-text", Static)
        challenge_text.update(f"🎯 {self.current_challenge.category}: {self.current_challenge.prompt}")
        
        timer_bar = self.query_one("#timer-bar", ProgressBar)
        timer_bar.total = self.current_challenge.time_limit
        timer_bar.progress = self.current_challenge.time_limit
        
        # Enable/disable buttons
        self.query_one("#start-round", Button).disabled = True
        self.query_one("#generate-ai", Button).disabled = False
        self.query_one("#submit", Button).disabled = False
        
        # Clear previous input
        response_input = self.query_one("#response-input", TextArea)
        response_input.text = ""
        response_input.placeholder = "Type your creative response here..."
        
        # Start timer
        self.start_timer()
    
    @work(exclusive=True)
    async def start_timer(self):
        """Count down the timer."""
        timer_bar = self.query_one("#timer-bar", ProgressBar)
        
        while self.time_remaining > 0 and self.game_state == "playing":
            await asyncio.sleep(1)
            self.time_remaining -= 1
            timer_bar.progress = self.time_remaining
            
        if self.time_remaining <= 0:
            self.end_round()
    
    @work(exclusive=True)
    async def generate_ai_response(self):
        """Generate AI response for the current challenge."""
        if not self.current_challenge:
            return
            
        self.game_state = "generating"
        
        # Update UI to show generating state
        response_input = self.query_one("#response-input", TextArea)
        response_input.text = "🤖 Generating AI response..."
        response_input.disabled = True
        
        self.query_one("#generate-ai", Button).disabled = True
        
        # Generate response
        ai_response = await self.game_engine.generate_ai_response(
            self.current_challenge.prompt,
            self.current_challenge.prompt
        )
        
        # Update UI with AI response
        response_input.text = ai_response
        response_input.disabled = False
        self.game_state = "playing"
        
        # Re-enable generate button for multiple attempts
        self.query_one("#generate-ai", Button).disabled = False
    
    def submit_response(self):
        """Submit the current response."""
        response_input = self.query_one("#response-input", TextArea)
        response_text = response_input.text.strip()
        
        if not response_text or response_text.startswith("🤖"):
            return
        
        # Submit to game engine
        self.game_engine.submit_response(self.player_id, response_text)
        self.end_round()
    
    def end_round(self):
        """End the current round and show results."""
        self.game_state = "results"
        
        # Update UI
        challenge_text = self.query_one("#challenge-text", Static)
        challenge_text.update("Round Complete! 🎉")
        
        timer_bar = self.query_one("#timer-bar", ProgressBar)
        timer_bar.progress = 0
        
        # Show results
        response_input = self.query_one("#response-input", TextArea)
        user_response = response_input.text.strip()
        
        results_text = self.query_one("#results-text", Static)
        if user_response and not user_response.startswith("🤖"):
            results_text.update(f"Your Response:\n\"{user_response}\"\n\nScore: +1 point for participation! 🌟")
            self.player.score += 1
        else:
            results_text.update("No response submitted. Try again next round!")
        
        # Reset buttons
        self.query_one("#start-round", Button).disabled = False
        self.query_one("#generate-ai", Button).disabled = True
        self.query_one("#submit", Button).disabled = True


class MultiplayerScreen(Screen):
    """Multiplayer screen."""

    def compose(self):
        """Create child widgets for multiplayer."""
        yield Header()
        with Container(id="multiplayer"):
            yield Static("👥 Multiplayer - Coming Soon!", id="multi-content")
            yield Button("← Back to Menu", id="back", variant="warning")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "back":
            self.app.pop_screen()


class PromptfallApp(App):
    """A Textual app for Promptfall."""

    CSS_PATH = "promptfall.tcss"
    SCREENS = {
        "menu": MenuScreen,
        "game": GameScreen,
        "multiplayer": MultiplayerScreen,
    }

    def on_mount(self) -> None:
        """Called when app starts."""
        self.push_screen("menu")


def main():
    """Run the app."""
    app = PromptfallApp()
    app.run()


if __name__ == "__main__":
    main()