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
        
        # Get user response
        response_input = self.query_one("#response-input", TextArea)
        user_response = response_input.text.strip()
        
        if user_response and not user_response.startswith("🤖"):
            # Create voting scenario with AI responses
            self.create_voting_scenario(user_response)
        else:
            self.show_no_response_result()
            
    def create_voting_scenario(self, user_response: str):
        """Create a voting scenario with user response vs AI responses."""
        # Generate AI responses for comparison
        ai_responses = [
            "In the grand symphony of existence, creativity dances with technology to birth infinite possibilities.",
            "Like whispers of imagination carried on digital winds, innovation blooms in the garden of human ingenuity.",
            "Through the kaleidoscope of progress, we glimpse tomorrow's dreams taking shape in today's reality."
        ]
        
        import random
        selected_ai_responses = random.sample(ai_responses, 2)
        
        # Create responses for voting
        responses_for_voting = [
            {"player_id": "player1", "player_name": "You", "response": user_response},
            {"player_id": "ai1", "player_name": "AI Assistant Alpha", "response": selected_ai_responses[0]},
            {"player_id": "ai2", "player_name": "AI Assistant Beta", "response": selected_ai_responses[1]}
        ]
        
        # Show voting screen
        from .voting import VotingScreen
        voting_screen = VotingScreen(
            responses_for_voting,
            self.cast_single_player_vote,
            self.show_single_player_results
        )
        self.app.push_screen(voting_screen)
        
    def cast_single_player_vote(self, target_player_id: str):
        """Handle voting in single player mode."""
        if target_player_id == "player1":
            self.player.score += 2  # Bonus for winning against AI
            self.voting_result = "You won against the AI! 🏆"
        else:
            self.player.score += 1  # Participation points
            self.voting_result = "Close match! You earned participation points. 🌟"
            
    def show_single_player_results(self):
        """Show single player round results."""
        self.app.pop_screen()  # Close voting screen
        
        # Update UI
        challenge_text = self.query_one("#challenge-text", Static)
        challenge_text.update("Round Complete! 🎉")
        
        timer_bar = self.query_one("#timer-bar", ProgressBar)
        timer_bar.progress = 0
        
        # Show results
        results_text = self.query_one("#results-text", Static)
        results_text.update(f"{getattr(self, 'voting_result', 'Round completed!')}\n\nTotal Score: {self.player.score} points")
        
        # Reset buttons
        self.query_one("#start-round", Button).disabled = False
        self.query_one("#generate-ai", Button).disabled = True
        self.query_one("#submit", Button).disabled = True
        
    def show_no_response_result(self):
        """Show result when no response was submitted."""
        # Update UI
        challenge_text = self.query_one("#challenge-text", Static)
        challenge_text.update("Round Complete! 🎉")
        
        timer_bar = self.query_one("#timer-bar", ProgressBar)
        timer_bar.progress = 0
        
        results_text = self.query_one("#results-text", Static)
        results_text.update("No response submitted. Try again next round!")
        
        # Reset buttons
        self.query_one("#start-round", Button).disabled = False
        self.query_one("#generate-ai", Button).disabled = True
        self.query_one("#submit", Button).disabled = True


class MultiplayerLobbyScreen(Screen):
    """Multiplayer lobby screen."""
    
    def __init__(self):
        super().__init__()
        self.available_rooms = []
        
    def compose(self):
        """Create lobby UI components."""
        yield Header()
        with Container(id="multiplayer-lobby"):
            with Vertical(id="lobby-content"):
                yield Static("👥 Multiplayer Lobby", id="lobby-title")
                
                # Room creation section
                with Container(id="create-room-section"):
                    yield Static("Create New Room:", classes="section-title")
                    with Horizontal(id="create-room-controls"):
                        yield Input(placeholder="Room name", id="room-name-input")
                        yield Button("Create Room", id="create-room", variant="primary")
                        
                # Join room section
                with Container(id="join-room-section"):
                    yield Static("Available Rooms:", classes="section-title")
                    yield Button("Refresh Rooms", id="refresh-rooms", variant="success")
                    yield Container(id="rooms-list")
                    
                # Player info section
                with Container(id="player-info-section"):
                    yield Static("Your Name:", classes="section-title")
                    with Horizontal(id="player-controls"):
                        yield Input(placeholder="Enter your name", id="player-name-input", value="Player")
                        
                yield Button("← Back to Menu", id="back", variant="error")
        yield Footer()
        
    def on_mount(self):
        """Called when screen is mounted."""
        self.refresh_room_list()
        
    def refresh_room_list(self):
        """Refresh the list of available rooms."""
        # This would connect to the server and get room list
        # For now, show placeholder
        rooms_container = self.query_one("#rooms-list")
        rooms_container.remove_children()
        
        # Placeholder rooms
        placeholder_rooms = [
            {"id": "room1", "name": "Quick Game", "player_count": 2, "max_players": 4},
            {"id": "room2", "name": "Competitive Match", "player_count": 1, "max_players": 4},
        ]
        
        for room in placeholder_rooms:
            room_widget = Container(
                Horizontal(
                    Static(f"{room['name']} ({room['player_count']}/{room['max_players']})", classes="room-name"),
                    Button("Join", id=f"join-{room['id']}", variant="primary", classes="join-room-btn"),
                    classes="room-item"
                ),
                classes="room-container"
            )
            rooms_container.mount(room_widget)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "back":
            self.app.pop_screen()
            
        elif button_id == "create-room":
            room_name = self.query_one("#room-name-input").value.strip()
            player_name = self.query_one("#player-name-input").value.strip()
            
            if room_name and player_name:
                # Create and join multiplayer game
                self.app.push_screen(MultiplayerGameScreen(player_name, room_name=room_name))
                
        elif button_id == "refresh-rooms":
            self.refresh_room_list()
            
        elif button_id.startswith("join-"):
            room_id = button_id.replace("join-", "")
            player_name = self.query_one("#player-name-input").value.strip()
            
            if player_name:
                # Join existing multiplayer game
                self.app.push_screen(MultiplayerGameScreen(player_name, room_id=room_id))


class MultiplayerGameScreen(Screen):
    """Multiplayer game screen."""
    
    game_state = reactive("lobby")  # lobby, playing, voting, results
    time_remaining = reactive(30)
    
    def __init__(self, player_name: str, room_name: str = None, room_id: str = None):
        super().__init__()
        self.player_name = player_name
        self.room_name = room_name
        self.room_id = room_id
        self.players = []
        self.current_challenge = None
        self.responses_for_voting = []
        self.is_host = room_name is not None  # Host if creating room
        
    def compose(self):
        """Create multiplayer game UI."""
        yield Header()
        with Container(id="multiplayer-game"):
            with Vertical(id="mp-game-content"):
                yield Static("👥 Multiplayer Game", id="mp-game-title")
                
                # Room info section
                with Container(id="room-info"):
                    yield Static("", id="room-status")
                    yield Container(id="players-list")
                    
                # Game section (hidden initially)
                with Container(id="game-section", classes="hidden"):
                    yield Static("", id="mp-challenge-text")
                    yield ProgressBar(total=30, show_eta=False, id="mp-timer-bar")
                    
                    # Response input
                    with Container(id="mp-input-area"):
                        yield TextArea(id="mp-response-input")
                        
                    # Game actions
                    with Horizontal(id="mp-game-actions"):
                        yield Button("Generate AI Response", id="mp-generate-ai", variant="success", disabled=True)
                        yield Button("Submit Response", id="mp-submit", variant="warning", disabled=True)
                        
                # Lobby actions
                with Horizontal(id="lobby-actions"):
                    yield Button("Start Game", id="start-mp-game", variant="primary", disabled=not self.is_host)
                    yield Button("Leave Room", id="leave-room", variant="error")
                    
                # Status area
                yield Container(
                    Static("", id="mp-status"),
                    id="mp-status-area"
                )
                
        yield Footer()
        
    def on_mount(self):
        """Called when screen is mounted."""
        self.update_room_status()
        self.simulate_room_join()
        
    def simulate_room_join(self):
        """Simulate joining a multiplayer room (placeholder for WebSocket integration)."""
        # Add current player
        self.players = [{"name": self.player_name, "id": "player1", "score": 0}]
        
        # Add some fake players for demonstration
        if self.room_id:  # Joining existing room
            self.players.extend([
                {"name": "Alice", "id": "player2", "score": 5},
                {"name": "Bob", "id": "player3", "score": 3}
            ])
        
        self.update_players_display()
        
    def update_room_status(self):
        """Update room status display."""
        room_name = self.room_name or f"Room {self.room_id}"
        status = f"Room: {room_name} | Players: {len(self.players)}/4"
        
        if self.is_host:
            status += " | You are the host"
            
        self.query_one("#room-status").update(status)
        
    def update_players_display(self):
        """Update the players list display."""
        players_container = self.query_one("#players-list")
        players_container.remove_children()
        
        for player in self.players:
            player_widget = Static(
                f"👤 {player['name']} (Score: {player['score']})",
                classes="player-item"
            )
            players_container.mount(player_widget)
            
        self.update_room_status()
        
    def start_multiplayer_game(self):
        """Start the multiplayer game."""
        if len(self.players) < 2:
            self.show_status("Need at least 2 players to start!")
            return
            
        self.game_state = "playing"
        
        # Simulate challenge
        challenges = [
            {"prompt": "Explain why pizza is the perfect food using only haikus", "category": "Creative", "time_limit": 45},
            {"prompt": "Write a customer service complaint about your pet", "category": "Humor", "time_limit": 30},
            {"prompt": "Describe a superhero whose power is extreme politeness", "category": "Comedy", "time_limit": 35},
        ]
        
        import random
        self.current_challenge = random.choice(challenges)
        self.time_remaining = self.current_challenge["time_limit"]
        
        # Update UI
        self.query_one("#game-section").remove_class("hidden")
        self.query_one("#lobby-actions").add_class("hidden")
        
        challenge_text = self.query_one("#mp-challenge-text")
        challenge_text.update(f"🎯 {self.current_challenge['category']}: {self.current_challenge['prompt']}")
        
        timer_bar = self.query_one("#mp-timer-bar")
        timer_bar.total = self.current_challenge["time_limit"]
        timer_bar.progress = self.current_challenge["time_limit"]
        
        # Enable game buttons
        self.query_one("#mp-generate-ai").disabled = False
        self.query_one("#mp-submit").disabled = False
        
        # Clear input
        self.query_one("#mp-response-input").text = ""
        
        self.show_status("Round started! Submit your response before time runs out!")
        self.start_timer()
        
    @work(exclusive=True)
    async def start_timer(self):
        """Start the game timer."""
        timer_bar = self.query_one("#mp-timer-bar")
        
        while self.time_remaining > 0 and self.game_state == "playing":
            await asyncio.sleep(1)
            self.time_remaining -= 1
            timer_bar.progress = self.time_remaining
            
        if self.time_remaining <= 0:
            self.start_voting_phase()
            
    def start_voting_phase(self):
        """Start the voting phase."""
        self.game_state = "voting"
        
        # Simulate other players' responses
        self.responses_for_voting = [
            {"player_id": "player2", "player_name": "Alice", "response": "Pizza haiku one: Cheese and sauce unite / Pepperoni dances free / Perfect harmony"},
            {"player_id": "player3", "player_name": "Bob", "response": "Dear Customer Service, My cat Kevin has been acting suspiciously polite lately and I demand an explanation."},
        ]
        
        # Add player's response if they submitted one
        player_response = self.query_one("#mp-response-input").text.strip()
        if player_response and not player_response.startswith("🤖"):
            self.responses_for_voting.insert(0, {
                "player_id": "player1",
                "player_name": self.player_name,
                "response": player_response
            })
            
        # Show voting screen
        from .voting import VotingScreen
        voting_screen = VotingScreen(
            self.responses_for_voting,
            self.cast_vote,
            self.show_results
        )
        self.app.push_screen(voting_screen)
        
    def cast_vote(self, target_player_id: str):
        """Cast a vote for another player."""
        # Find the target player and award points
        for player in self.players:
            if player["id"] == target_player_id:
                player["score"] += 1
                break
                
        self.show_status(f"Vote cast! Waiting for other players...")
        
        # Simulate other votes and show results after delay
        asyncio.create_task(self.delayed_results())
        
    async def delayed_results(self):
        """Show results after a delay."""
        await asyncio.sleep(2)
        self.show_results()
        
    def show_results(self):
        """Show round results."""
        self.game_state = "results"
        
        # Sort players by score
        sorted_players = sorted(self.players, key=lambda x: x["score"], reverse=True)
        
        results = []
        for player in sorted_players:
            # Find their response
            response = "No response submitted"
            for resp in self.responses_for_voting:
                if resp["player_id"] == player["id"]:
                    response = resp["response"]
                    break
                    
            results.append({
                "player_id": player["id"],
                "player_name": player["name"],
                "response": response,
                "score": player["score"]
            })
            
        # Show results screen
        from .voting import ResultsScreen
        results_screen = ResultsScreen(
            results,
            self.next_round,
            self.return_to_lobby
        )
        self.app.push_screen(results_screen)
        
    def next_round(self):
        """Start the next round."""
        self.app.pop_screen()  # Close results screen
        self.start_multiplayer_game()  # Start new round
        
    def return_to_lobby(self):
        """Return to the multiplayer lobby."""
        self.app.pop_screen()  # Close results screen
        self.app.pop_screen()  # Close game screen
        
    @work(exclusive=True)
    async def generate_ai_response(self):
        """Generate AI response for multiplayer."""
        if not self.current_challenge:
            return
            
        response_input = self.query_one("#mp-response-input")
        response_input.text = "🤖 Generating AI response..."
        response_input.disabled = True
        
        self.query_one("#mp-generate-ai").disabled = True
        
        # Simulate AI generation (use actual AI in real implementation)
        await asyncio.sleep(2)
        
        ai_responses = [
            "In the grand theater of culinary excellence, pizza stands as the ultimate performer.",
            "Like a symphony of flavors dancing on your taste buds, pizza achieves perfect harmony.",
            "Through the lens of gastronomic innovation, pizza represents humanity's greatest achievement.",
        ]
        
        import random
        ai_response = random.choice(ai_responses)
        
        response_input.text = ai_response
        response_input.disabled = False
        self.query_one("#mp-generate-ai").disabled = False
        
    def show_status(self, message: str):
        """Show a status message."""
        self.query_one("#mp-status").update(message)
        
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "leave-room":
            self.app.pop_screen()
            
        elif button_id == "start-mp-game":
            self.start_multiplayer_game()
            
        elif button_id == "mp-generate-ai":
            self.generate_ai_response()
            
        elif button_id == "mp-submit":
            self.submit_multiplayer_response()
            
    def submit_multiplayer_response(self):
        """Submit response in multiplayer game."""
        response_input = self.query_one("#mp-response-input")
        response_text = response_input.text.strip()
        
        if not response_text or response_text.startswith("🤖"):
            self.show_status("Please enter a response first!")
            return
            
        self.show_status("Response submitted! Waiting for other players...")
        
        # Disable submit button
        self.query_one("#mp-submit").disabled = True
        
        # Simulate waiting for other players, then start voting
        asyncio.create_task(self.delayed_voting())
        
    async def delayed_voting(self):
        """Start voting after a delay."""
        await asyncio.sleep(3)
        self.start_voting_phase()


class MultiplayerScreen(Screen):
    """Multiplayer mode selection screen."""

    def compose(self):
        """Create multiplayer mode selection."""
        yield Header()
        with Container(id="multiplayer"):
            with Vertical(id="mp-menu"):
                yield Static("👥 Multiplayer Mode", id="mp-title")
                yield Static("Play against other humans in real-time!", id="mp-subtitle")
                yield Button("Join Lobby", id="join-lobby", variant="primary")
                yield Button("How to Play", id="how-to-play", variant="success")
                yield Button("← Back to Menu", id="back", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "join-lobby":
            self.app.push_screen(MultiplayerLobbyScreen())
        elif event.button.id == "how-to-play":
            self.show_how_to_play()
            
    def show_how_to_play(self):
        """Show how to play instructions."""
        # This could be implemented as another screen or modal
        pass


class PromptfallApp(App):
    """A Textual app for Promptfall."""

    CSS_PATH = "promptfall.tcss"
    SCREENS = {
        "menu": MenuScreen,
        "game": GameScreen,
        "multiplayer": MultiplayerScreen,
        "multiplayer_lobby": MultiplayerLobbyScreen,
        "multiplayer_game": MultiplayerGameScreen,
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