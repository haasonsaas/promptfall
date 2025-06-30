# ⚔️ Promptfall
<img width="912" alt="Screenshot 2025-06-29 at 9 06 12 PM" src="https://github.com/user-attachments/assets/d554aeb6-11aa-4203-b748-45c8bc886902" />


A competitive real-time prompt dueling game that combines the fast-paced action of Tetris Attack with the creativity of Cards Against Humanity and the power of GPT.

## 🎮 Game Concept

Promptfall is a real-time competitive game where players:
- Receive prompt challenges under time pressure
- Generate creative AI responses using OpenAI's GPT
- Vote on the best responses
- Compete in fast-paced dueling matches

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/haasonsaas/promptfall.git
cd promptfall

# Create and activate virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy environment file and add your OpenAI API key
cp .env.example .env
# Edit .env with your OpenAI API key
```

## 🎯 Usage

```bash
# Activate virtual environment first
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the game
promptfall

# Or run directly with Python
python -m promptfall.main
```

## 🔧 Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
ruff check .
```

## 📝 License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

## 👨‍💻 Author

**Jonathan Haas** (jonathan@haas.holdings) - 2025

## 🛠️ Built With

- [Textual](https://github.com/Textualize/textual) - Modern Python TUI framework
- [OpenAI API](https://openai.com/api/) - AI response generation
- WebSockets - Real-time multiplayer support
