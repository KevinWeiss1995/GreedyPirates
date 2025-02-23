import asyncio
import sys
import aioconsole
from typing import Optional, Dict
from ..network.client import GameClient
from ..network.messages import MessageType, Message, StartRoundMessage, EndRoundMessage, GameOverMessage, ErrorMessage
from ..utils.config import Config
from ..utils.logger import GameLogger

class ConsoleUI:
    def __init__(self):
        self.config = Config()
        self.logger = GameLogger("console_ui", "logs/ui.log")
        self.client: Optional[GameClient] = None
        self.running = False
        self.current_round = 0
        self._round_active = False
        
    async def start(self):
        """Start the console UI"""
        print("Welcome to Greedy Pirates!")
        
        # Get player name
        player_name = await aioconsole.ainput("Enter your name: ")
        
        # Get server details
        host = await aioconsole.ainput("Enter server host (default: localhost): ")
        port = await aioconsole.ainput("Enter server port (default: 8888): ")
        
        # Create and connect client
        try:
            self.client = GameClient(
                host=host if host else None,
                port=int(port) if port else None
            )
            
            # Register message handlers
            self.client.register_handler(MessageType.START_ROUND, self.handle_start_round)
            self.client.register_handler(MessageType.END_ROUND, self.handle_end_round)
            self.client.register_handler(MessageType.GAME_OVER, self.handle_game_over)
            self.client.register_handler(MessageType.ERROR, self.handle_error)
            
            # Connect to server
            if await self.client.connect(player_name):
                print("Connected to server at {}:{}".format(
                    self.client.host, self.client.port
                ))
                print("Joined game successfully")
                print("Waiting for other players to join...")
                
                # Set running state
                self.running = True
                
                # Start message receiving loop
                receive_task = asyncio.create_task(self.client.receive_messages())
                
                # Start command input loop
                input_task = asyncio.create_task(self.input_loop())
                
                # Wait for both tasks
                await asyncio.gather(receive_task, input_task)
            else:
                print("Failed to connect to server")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if self.client:
                self.client.stop()
    
    async def input_loop(self):
        """Handle user input"""
        while self.running:
            try:
                command = await aioconsole.ainput("> ")
                await self.handle_command(command)
            except Exception as e:
                print(f"Error processing command: {e}")
    
    async def handle_command(self, command: str):
        """Process user commands"""
        parts = command.lower().split()
        if not parts:
            return
            
        cmd = parts[0]
        
        if cmd == "bid":
            if len(parts) != 2:
                print("Usage: bid <amount>")
                return
            try:
                amount = int(parts[1])
                await self.place_bid(amount)
            except ValueError:
                print("Bid amount must be a number")
                
        elif cmd == "help":
            self.show_help()
            
        elif cmd == "quit":
            self.running = False
            if self.client:
                self.client.stop()
            
        else:
            print(f"Unknown command: {cmd}")
            self.show_help()
    
    async def place_bid(self, amount: int):
        """Place a bid in the current round"""
        print(f"DEBUG: Attempting to place bid. _round_active = {self._round_active}")  # Debug log
        
        if not self.client:
            print("Cannot bid - not connected to server")
            return
            
        if not self._round_active:
            print("Cannot bid now - waiting for round to start")
            print(f"DEBUG: Bid rejected - round not active")  # Debug log
            return
            
        try:
            await self.client.send_bid(amount)
            print(f"Placed bid of {amount}")
        except Exception as e:
            print(f"Error placing bid: {e}")
    
    async def handle_start_round(self, message: Message):
        """Handle start of round message"""
        print("DEBUG: Received START_ROUND message")  # Debug log
        self.current_round = message.data.get('round', 1)
        self._round_active = True
        if self.client:
            self._round_active = self.client._round_active  # Sync with client's state
        print(f"DEBUG: ConsoleUI round_active = {self._round_active}")  # Debug log
        
        print(f"\nRound {self.current_round} started!")
        print("Enter your bid with: bid <amount>")
    
    async def handle_end_round(self, message: Message):
        """Handle end of round message"""
        print("\n=== ConsoleUI: Processing Round End ===")  # Added marker
        self._round_active = False
        results = message.data.get('results', {})
        print(f"DEBUG: ConsoleUI received results: {results}")  # Added debug
        
        print("\n=== Round Results ===")
        for player_id, result in results.items():
            print(f"DEBUG: Processing result for player {player_id}: {result}")  # Added debug
            if isinstance(result, dict):
                name = result.get('name', player_id)
                bid = result.get('bid', '?')
                share = result.get('share', '?')
                print(f"{name}: bid {bid}, received {share} gold")
            else:
                print(f"Player {player_id}: {result}")
        print("==================\n")
        
        print(f"DEBUG: ConsoleUI finished processing round end")  # Added debug
        print(f"Round {self.current_round + 1} started!")
        print("Enter your bid with: bid <amount>")
    
    async def handle_game_over(self, message: Message):
        """Handle game over"""
        scores = message.data.get("final_scores", {})
        print("\nGame Over!")
        print("Final Scores:")
        for player, score in scores.items():
            print(f"{player}: {score}")
        self.running = False
        if self.client:
            self.client.stop()
    
    async def handle_error(self, message: Message):
        """Handle error messages from server"""
        error_msg = message.data.get('error', 'Unknown error')
        print(f"\nServer Error: {error_msg}")
    
    def show_help(self):
        """Show available commands"""
        print("\nAvailable commands:")
        print("  bid <amount>  - Place a bid in the current round")
        print("  help         - Show this help message")
        print("  quit         - Exit the game")

def main():
    ui = ConsoleUI()
    try:
        asyncio.run(ui.start())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if ui.client:
            ui.client.stop()

if __name__ == "__main__":
    main()
