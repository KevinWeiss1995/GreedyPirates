import asyncio
import socket
import subprocess
import netifaces
import uuid
import json
import time
from typing import Dict, Set, Optional, List
from .protocol import Protocol
from .messages import (
    Message, MessageType, JoinMessage, BidMessage,
    StartRoundMessage, EndRoundMessage, GameOverMessage, ErrorMessage
)
from ..core.game_state import GameState
from ..utils.config import Config
from ..utils.logger import GameLogger

class BidProcessingError(Exception):
    """Error during bid processing"""
    pass

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
        self.player_keys: Dict[str, str] = {}  # Store public keys
        
        self.logger.info(f"Server initialized on {self.host}:{self.port}")
        
    def get_ipv6_address(self) -> str:
        """Get the machine's IPv6 address"""
        try:
            # Get all network interfaces
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                # Look for IPv6 addresses
                if netifaces.AF_INET6 in addrs:
                    for addr in addrs[netifaces.AF_INET6]:
                        # Skip localhost (::1) and other special addresses
                        if not addr['addr'].startswith('fe80') and addr['addr'] != '::1':
                            return addr['addr']
            return None
        except Exception as e:
            self.logger.error(f"Failed to get IPv6 address: {e}")
            return None

    async def start(self):
        """Start the server"""
        try:
            # Create socket for IPv6
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Get the machine's IPv6 address
            ipv6_addr = self.get_ipv6_address()
            
            # Bind to all interfaces
            bind_addr = '::'
            self.logger.info(f"Binding to [{bind_addr}]:{self.port}")
            sock.bind((bind_addr, self.port))
            self.logger.info("Bind successful")
            
            server = await asyncio.start_server(
                self.handle_client,
                sock=sock
            )
            
            self.running = True
            
            # Print connection information
            print(f"\nServer is ready for connections!")
            print(f"Local clients can connect using: localhost")
            if ipv6_addr:
                print(f"Remote clients can connect using: [{ipv6_addr}]:{self.port}")
            else:
                print("Warning: Could not detect IPv6 address")
            
            async with server:
                await server.serve_forever()
                
        except Exception as e:
            self.logger.error(f"Server start error: {e}")
            raise
            
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        # Each player gets a short random ID
        client_id = f"p{uuid.uuid4().hex[:3]}"
        try:
            self.logger.info(f"New player connected: {client_id}")
            
            while True:
                try:
                    data = await reader.readline()
                    if not data:
                        break
                        
                    message_str = data.decode().strip()
                    if not message_str:
                        continue
                        
                    message = Protocol.deserialize(message_str)
                    
                    if message.type == MessageType.JOIN:
                        await self.handle_join(client_id, message, writer)
                    elif message.type == MessageType.BID:
                        await self.handle_bid(client_id, message)
                    else:
                        self.logger.warning(f"Unknown message from {client_id}: {message.type}")
                        
                except json.JSONDecodeError:
                    # Ignore empty or malformed messages
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing message from {client_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Connection error for {client_id}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"\nPlayer disconnected: {self.player_names.get(client_id, client_id)}")
            if client_id in self.clients:
                del self.clients[client_id]
                del self.player_names[client_id]
                if client_id in self.player_keys:
                    del self.player_keys[client_id]
                    
    async def broadcast_message(self, message: Message):
        """Send a message to all connected clients"""
        print(f"\nBroadcasting: {message.type}")
        print(f"Current players: {list(self.player_names.values())}")
        
        for client_id, writer in self.clients.items():
            try:
                await self.send_message(writer, message)
                print(f"Sent to {self.player_names[client_id]}")
            except Exception as e:
                print(f"Failed to send to {self.player_names[client_id]}: {e}")
                self.logger.error(f"Broadcast error: {e}")
                
    async def send_message(self, writer: asyncio.StreamWriter, message: Message):
        """Send a single message to one player"""
        try:
            data = Protocol.serialize(message)
            writer.write(data)
            await writer.drain()
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise  # Re-raise to handle disconnection
    
    async def send_error(self, writer: asyncio.StreamWriter, error: str):
        """Send an error message to a specific client"""
        message = ErrorMessage(error)
        data = Protocol.serialize(message)
        try:
            writer.write(data)
            await writer.drain()
        except Exception as e:
            self.logger.error(f"Error sending error message: {e}")
    
    async def handle_join(self, client_id: str, message: JoinMessage, writer: asyncio.StreamWriter):
        """Handle a player joining the game"""
        try:
            player_name = message.data['player_name']
            public_key = message.data.get('public_key', '')
            
            print(f"\n=== Player Join: {player_name} ===")
            
            # Add new player to our lists
            self.clients[client_id] = writer
            self.player_names[client_id] = player_name
            self.player_keys[client_id] = public_key
            
            # Add player to game state
            self.game_state.add_player(client_id, player_name)  # Make sure player is added to game state
            
            print(f"Total players now: {len(self.clients)}")
            print(f"Players: {list(self.player_names.values())}")
            
            # Broadcast join to other players
            join_msg = JoinMessage(client_id, player_name, public_key)
            for other_id, other_writer in self.clients.items():
                if other_id != client_id:
                    await self.send_message(other_writer, join_msg)
            
            # Check if we should start the game (exactly 3 players)
            if len(self.clients) == 3:
                print("\n=== Starting New Game ===")
                print(f"Players ({len(self.clients)}): {list(self.player_names.values())}")
                
                # Start the game state
                self.game_state.start_round()  # This will set round_active to True
                print(f"DEBUG: Server game_state.round_active = {self.game_state.round_active}")
                
                # Start first round immediately
                start_msg = StartRoundMessage(1)
                print("DEBUG: Server sending START_ROUND message")
                await self.broadcast_message(start_msg)
                print("DEBUG: START_ROUND message sent")
            
            print("======================\n")
                
        except Exception as e:
            print(f"Error handling join: {e}")
            self.logger.error(f"Join error: {e}")
            if client_id in self.clients:
                del self.clients[client_id]
                
    async def handle_bid(self, client_id: str, message: BidMessage):
        """Handle a bid from a client"""
        try:
            print(f"\nReceived bid from {self.player_names[client_id]}")
            
            # Validate bid encryption
            encrypted_bids = message.data.get('encrypted_bids', {})
            if not encrypted_bids:
                raise ValueError("No encrypted bids received")
                
            # Store the bid using place_bid instead of add_bid
            self.game_state.place_bid(client_id, encrypted_bids)
            print(f"Stored bid. Total bids received: {len(self.game_state.bids)}")
            
            # Check if round is complete
            if len(self.game_state.bids) == len(self.clients):
                print("\nAll bids received - ending round")
                await self.end_round()
                
        except Exception as e:
            print(f"Error handling bid: {e}")
            self.logger.error(f"Bid error: {e}")
            await self.send_error(self.clients[client_id], str(e))
            
    async def end_round(self):
        """End the current round"""
        try:
            print("\n=== Server: Ending Round ===")  # Added marker
            
            # Calculate results using calculate_round_results
            results = self.game_state.calculate_round_results()
            print(f"DEBUG: Server calculated results: {results}")
            
            # Create end round message
            end_msg = EndRoundMessage(
                round_num=self.game_state.current_round,
                results=results
            )
            print(f"DEBUG: Server created END_ROUND message: {end_msg.data}")  # Added debug
            
            # Send end round message to all players
            print("DEBUG: Server broadcasting END_ROUND message")
            await self.broadcast_message(end_msg)
            print("DEBUG: Server finished broadcasting END_ROUND")
            
            print(f"Round {self.game_state.current_round} ended")
            
            # Reset for next round
            self.game_state.reset_round()
            
            # Start next round after a short delay
            await asyncio.sleep(2)
            await self.start_round()
            
        except Exception as e:
            print(f"Error ending round: {e}")
            self.logger.error(f"Round end error: {e}")
            
    async def end_game(self):
        """End the game and broadcast final scores"""
        self.logger.info("Game over")
        await self.broadcast_message(GameOverMessage(
            final_scores=self.game_state.get_final_scores()
        ))
        self.running = False

    async def handle_disconnect(self, client_id: str):
        """Handle a client disconnecting"""
        if client_id in self.clients:
            print(f"\n=== Player Disconnected ===")
            print(f"Player: {self.player_names.get(client_id, 'Unknown')}")
            
            # Clean up player data
            del self.clients[client_id]
            self.player_names.pop(client_id, None)
            self.player_keys.pop(client_id, None)
            
            print(f"Remaining players: {list(self.player_names.values())}")
            print("========================\n")
            
            # If too few players, end the round
            if len(self.clients) < 3 and self.game_state.round_active:
                print("Not enough players - ending round")
                self.game_state.round_active = False
                end_msg = EndRoundMessage(self.game_state.current_round)
                await self.broadcast_message(end_msg)

    async def start_round(self):
        """Start a new round"""
        try:
            print("\nStarting new round...")
            self.game_state.start_round()  # This increments current_round
            
            # Create and send START_ROUND message with current round number
            start_msg = StartRoundMessage(
                round_num=self.game_state.current_round
            )
            
            await self.broadcast_message(start_msg)
            print(f"Round {self.game_state.current_round} started - waiting for bids")
            
        except Exception as e:
            print(f"Error starting round: {e}")
            self.logger.error(f"Round start error: {e}")
