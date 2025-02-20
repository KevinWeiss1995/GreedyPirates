# Greedy Pirates

A multiplayer bidding game where pirates compete to get the largest share of treasure through strategic bidding.

## Game Description

In Greedy Pirates, players are pirates trying to get the biggest share of treasure over multiple rounds. Each round, there's a treasure of 100 gold pieces, and players must bid simultaneously to get their share. The gold is distributed proportionally based on bids.

### Game Rules
- Each round has a treasure of 100 gold pieces.
- Players make secret bids simultaneously.
- Gold is distributed proportionally to bids.
- If everyone bids 0, the gold is split equally.
- The game continues for 10 rounds.
- The player with the most gold at the end wins.

### Strategy
The key to winning is predicting what other players will bid and adjusting your strategy accordingly. Bid too high and you might waste gold, bid too low and you might get a tiny share!

## Installation

1. Clone the repository:

   ```bash
   git clone git@github.com:KevinWeiss1995/GreedyPirates.git
   cd GreedyPirates
   ```

2. Make sure you have Python 3.7+ installed.

3. Install dependencies:

   ```bash
   pip install asyncio aioconsole
   ```

4. Start the server:

   ```bash
   python3 main.py --server
   ```

5. In separate terminal windows, start each client (minimum 3 players required):

   ```bash
   python3 main.py
   ```

6. Follow the prompts to:
   - Enter your name.
   - Connect to the server (default: localhost:8888).
   - Place bids when prompted.

## Game Commands

- `bid <amount>` - Place a bid in the current round.
- `help` - Show available commands.
- `quit` - Exit the game.

## Technical Details

- Built with Python 3.7+
- Uses asyncio for network communication.
- Supports multiple simultaneous players.
- Implements a client-server architecture.

## Contributing

Feel free to submit issues and enhancement requests!

## License

[MIT License](LICENSE)
