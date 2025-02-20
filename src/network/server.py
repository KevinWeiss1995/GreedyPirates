import asyncio
import socket
import subprocess
from typing import Dict, Set, Optional, List
from .protocol import Protocol
from .messages import (
    Message, MessageType, JoinMessage, BidMessage,
    StartRoundMessage, EndRoundMessage, GameOverMessage, ErrorMessage
)
from ..core.game_state import GameState
from ..utils.config import Config
from ..utils.logger import GameLogger

class GameServer:
    def __init__(self, host: str = None, port: int = None):
        # Load config
        self.config = Config()
        self.logger = GameLogger("game_server", "logs/server.log")
        
        # Use config values or fallback to parameters
        self.host = host or self.config.get("server", "host")
        self.port = port or self.config.get("server", "port")
        
        self.clients: Dict[str, asyncio.StreamWriter] = {}
        self.player_names: Dict[str, str] = {}
        self.game_state = GameState(
            min_players=self.config.get("game", "min_players"),
            max_players=self.config.get("game", "max_players"),
            max_rounds=self.config.get("game", "max_rounds")
        )
        self.running = False
        
        self.logger.info(f"Server initialized on {self.host}:{self.port}")
        
    async def start(self):
        """Start the server"""
        try:
            # Print network info
            print("\nServer Network Configuration:")
            print("----------------------------")
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            print(result.stdout)
            
            # Create server
            server = await asyncio.start_server(
                self.handle_client,
                host='::',  # Listen on all IPv6 interfaces
                port=self.port,
                family=socket.AF_INET6,
                reuse_address=True
            )
            
            self.running = True
            
            # Print detailed binding information
            for sock in server.sockets:
                print(f"\nSocket Information:")
                print(f"Local Address: {sock.getsockname()}")
                print(f"Socket Family: {sock.family}")
                print(f"Socket Type: {sock.type}")
                
            print("\nServer is ready for connections!")
            print(f"Local clients can connect using: localhost:{self.port}")
            print(f"Remote clients can connect using: [2606:69c0:9120:5403::2585]:{self.port}")
            
            async with server:
                await server.serve_forever()
                
        except Exception as e:
            self.logger.error(f"Server start error: {e}")
            print(f"\nError starting server: {e}")
            print("Try running with sudo if this is a permission error")
            raise
            
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a client connection"""
        client_id = None
        
        try:
            while self.running:
                data = await reader.readline()
                if not data:
                    break
                    
                message = Protocol.deserialize(data)
                if not message:
                    continue
                    
                self.logger.info(f"Received message: {message}")
                
                if message.type == MessageType.JOIN:
                    client_id = message.player_id
                    player_name = message.data['player_name']
                    
                    self.clients[client_id] = writer
                    self.player_names[client_id] = player_name
                    self.game_state.add_player(client_id, player_name)
                    
                    self.logger.info(f"Player {player_name} ({client_id}) joined")
                    
                    # Check if we have enough players to start
                    if len(self.clients) >= self.game_state.min_players:
                        await self.start_game()
                        
                elif message.type == MessageType.BID:
                    if not client_id:
                        await self.send_error(writer, "Not joined to game")
                        continue
                        
                    await self.handle_bid(client_id, message)
                    
        except Exception as e:
            self.logger.error(f"Error handling client: {e}")
            if client_id:
                await self.send_error(writer, str(e))
                
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
                self.game_state.remove_player(client_id)
                if client_id in self.player_names:
                    del self.player_names[client_id]
                self.logger.info(f"Client {client_id} disconnected")
            
            writer.close()
            await writer.wait_closed()
            
    async def broadcast_message(self, message: Message):
        """Send a message to all connected clients"""
        data = Protocol.serialize(message)
        for writer in self.clients.values():
            try:
                writer.write(data)
                await writer.drain()
            except Exception as e:
                self.logger.error(f"Error broadcasting message: {e}")
                
    async def send_error(self, writer: asyncio.StreamWriter, error: str):
        """Send an error message to a specific client"""
        message = ErrorMessage(error)
        data = Protocol.serialize(message)
        try:
            writer.write(data)
            await writer.drain()
        except Exception as e:
            self.logger.error(f"Error sending error message: {e}")
    
    async def start_game(self):
        """Start the game"""
        self.logger.info("Starting game")
        # Initialize game state before starting first round
        self.game_state.current_round = 0  # Reset to 0 before first start_round()
        self.game_state.start_round()  # This will increment to 1
        await self.broadcast_message(StartRoundMessage(self.game_state.current_round))
    
    async def handle_bid(self, client_id: str, message: BidMessage):
        """Handle a bid from a client"""
        try:
            bid_value = message.data.get('value', 0)
            self.logger.info(f"Processing bid of {bid_value} from {client_id}")
            
            self.game_state.place_bid(client_id, bid_value)
            
            if self.game_state.all_bids_placed():
                results = self.game_state.calculate_round_results()
                await self.broadcast_message(EndRoundMessage(
                    round_num=self.game_state.current_round,
                    results=results
                ))
                
                if self.game_state.is_game_over():
                    await self.end_game()
                else:
                    self.game_state.start_round()
                    await self.broadcast_message(StartRoundMessage(
                        self.game_state.current_round
                    ))
                    
        except Exception as e:
            self.logger.error(f"Error handling bid: {e}")
            await self.send_error(self.clients[client_id], f"Invalid bid format: {e}")
            
    async def end_game(self):
        """End the game and broadcast final scores"""
        self.logger.info("Game over")
        await self.broadcast_message(GameOverMessage(
            final_scores=self.game_state.get_final_scores()
        ))
        self.running = False
