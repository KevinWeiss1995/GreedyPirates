import asyncio
import uuid
import socket
import base64
from typing import Dict, Optional, Callable, Any
from asyncio import StreamReader, StreamWriter
from .protocol import Protocol
from .messages import Message, MessageType, JoinMessage, BidMessage, SessionKeyMessage
from ..crypto.keys import KeyManager
from ..utils.config import Config
from ..utils.logger import GameLogger
from enum import Enum
import logging
import json

class BidError(Exception):
    """Base class for bid-related errors"""
    pass

class EncryptionError(BidError):
    """Error during encryption/decryption"""
    pass

class VerificationError(BidError):
    """Error during bid verification"""
    pass

class GameClient:
    def __init__(self, host: str = None, port: int = None):
        self.config = Config()
        self.logger = GameLogger("game_client", "logs/client.log")
        
        self.host = host or self.config.get("server", "host")
        self.port = port or self.config.get("server", "port")
        
        self.player_id = f"p{uuid.uuid4().hex[:3]}"
        self.reader: Optional[StreamReader] = None
        self.writer: Optional[StreamWriter] = None
        self.running = False
        self.handlers: Dict[MessageType, Callable] = {}
        self.key_manager = KeyManager()
        self.session_keys: Dict[str, bytes] = {}
        self._round_active = False
        
    
        self.player_names = {}  
        self.player_keys = {}  
        
        self.logger.info("Initialized GameClient with round_active = False")
        
    def set_round_active(self, value: bool):
        """Set the round active state"""
        old_value = self._round_active
        self._round_active = value
        self.logger.info(f"round_active changed from {old_value} to {value}")
        
    def register_handler(self, msg_type: MessageType, handler: Callable[[Message], None]):
        """Register a handler for a specific message type"""
        self.handlers[msg_type] = handler
    
    async def start(self):
        """Start the client and handle messages"""
        try:
            print("Welcome to Greedy Pirates!")
            name = input("Enter your name: ")
            
            if not self.host:
                self.host = input("Enter server host (default: localhost): ") or 'localhost'
            if not self.port:
                port_str = input("Enter server port (default: 8888): ") or '8888'
                self.port = int(port_str)
                
            # Connect and join game
            if await self.connect(name):
                print("Joined game successfully")
                print("Waiting for other players to join...")
                
                # ONLY create the command handling task
                command_task = asyncio.create_task(self.handle_commands())
                
                # Use receive_messages directly instead of creating another task
                await asyncio.gather(
                    self.receive_messages(),
                    command_task
                )
                    
            else:
                print("Failed to join game")
                
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
                
    async def connect(self, player_name: str) -> bool:
        """Connect to the server and join the game"""
        try:
            # Generate keypair
            self.key_manager.generate_keypair()
            print("Generated RSA keypair\n")
            
            # Connect to server
            print(f"Attempting connection to {self.host}:{self.port}")
            self.reader, self.writer = await asyncio.open_connection(
                self.host,
                self.port
            )
            print(f"Connection established!")
            
            # Get public key as PEM string
            public_key = self.key_manager.get_public_key_string()
            
            # Create join message with all required arguments
            join_msg = JoinMessage(
                player_id=self.player_id,
                player_name=player_name,
                public_key=public_key
            )
            
            await self.send_message(join_msg)
            self.running = True
            return True
            
        except Exception as e:
            print(f"Connection failed: {e}")
            print("Failed to connect to server")
            return False
    
    async def send_message(self, message: Message):
        """Send a message to the server"""
        if not self.writer:
            raise ConnectionError("Not connected to server")
            
        try:
            data = Protocol.serialize(message)
            self.writer.write(data)
            await self.writer.drain()
            self.logger.info(f"Sent message type: {message.type}")
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            raise
    
    async def handle_commands(self):
        """Handle user input commands"""
        while self.running:
            try:
                command = await asyncio.get_event_loop().run_in_executor(
                    None, input
                )
                
                if command.startswith('bid '):
                    try:
                        amount = command.split()[1]
                        await self.send_bid(amount)
                    except IndexError:
                        print("Usage: bid <amount>")
                elif command == 'quit':
                    self.running = False
                    break
                else:
                    print("Unknown command. Available commands: bid <amount>, quit")
                    
            except Exception as e:
                self.logger.error(f"Error handling command: {e}")
                
    async def send_bid(self, amount: int):
        """Send a bid to the server"""
        try:
            # Add debug logging
            print(f"\nDebug: Current round_active state: {self._round_active}")
            
            if not self._round_active:
                print("Cannot bid now - round not active")
                return
                
            # Convert string amount to integer
            try:
                amount = int(amount)
            except ValueError:
                print("Bid amount must be a number")
                return
                
            print("\nDebug: Preparing bid encryption")
            print(f"Debug: Current players: {list(self.player_names.values())}")
            print(f"Debug: Available player keys: {list(self.player_keys.keys())}")
            
            # Encrypt bid for each player
            encrypted_bids = {}
            for player_id, player_key in self.player_keys.items():
                if player_id != self.player_id:
                    try:
                        # Convert bid to string and encrypt
                        bid_str = str(amount)
                        encrypted_bid = self.key_manager.encrypt(
                            bid_str.encode(),
                            player_key
                        )
                        encrypted_bids[player_id] = encrypted_bid.decode()
                        print(f"Debug: Successfully encrypted bid for {player_id}")
                    except Exception as e:
                        print(f"Debug: Failed to encrypt for {player_id}: {e}")
                        raise  # Re-raise to see full error
            
            print(f"Debug: Encrypted bids for {len(encrypted_bids)} players")
            
            # Create bid message with encrypted data
            bid_msg = BidMessage({
                'encrypted_bids': encrypted_bids,
                'player_id': self.player_id
            })
            
            await self.send_message(bid_msg)
            print("Bid submitted successfully")
            
        except Exception as e:
            print(f"Error sending bid: {e}")
            self.logger.error(f"Bid error: {e}")
            raise  # Add raise to see full error
    
    async def handle_peer_joined(self, message: Message):
        """Handle new peer joining with their public key"""
        peer_id = message.player_id
        peer_key = message.data.get('public_key')
        if peer_key:
            self.key_manager.load_peer_key(peer_id, peer_key)
            # Generate and send session key
            session_key = self.key_manager.generate_session_key()
            self.session_keys[peer_id] = session_key
            encrypted_key = self.key_manager.encrypt_session_key(session_key, peer_id)
            key_msg = SessionKeyMessage(peer_id, base64.b64encode(encrypted_key).decode('utf-8'))
            await self.send_message(key_msg)
    
    async def handle_bid(self, message: Message):
        """Handle encrypted bids from other players"""
        try:
            encrypted_bids = message.data.get('encrypted_bids', {})
            
            if not encrypted_bids:
                raise ValueError("Received empty bid data")
                
            if self.player_id not in encrypted_bids:
                self.logger.info("Received bid not intended for this player")
                return
                
            encrypted_bid = base64.b64decode(encrypted_bids[self.player_id])
            session_key = self.session_keys.get(message.player_id)
            
            if not session_key:
                raise EncryptionError(f"No session key for player {message.player_id}")
                
            try:
                decrypted_data = self.key_manager.decrypt_with_session_key(
                    session_key,
                    encrypted_bid
                )
                bid_value = int(decrypted_data.decode('utf-8'))
                
                # Validate decrypted bid
                if bid_value < 0:
                    raise VerificationError("Decrypted invalid bid value")
                    
                self.logger.info(f"Decrypted valid bid from {message.player_id}: {bid_value}")
                
            except ValueError as e:
                raise VerificationError(f"Invalid bid format: {e}")
            except Exception as e:
                raise EncryptionError(f"Decryption failed: {e}")
                
        except BidError as e:
            self.logger.error(f"Bid processing error: {e}")
            print(f"\nError processing bid from {message.player_id}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error handling bid: {e}")
            print("\nUnexpected error processing bid. The game may be unstable.")
    
    async def handle_session_key(self, message: Message):
        """Handle incoming session key"""
        if message.data.get('target_id') == self.player_id:
            encrypted_key = base64.b64decode(message.data['encrypted_key'])
            try:
                session_key = self.key_manager.decrypt_session_key(encrypted_key)
                self.session_keys[message.player_id] = session_key
                self.logger.info(f"Received session key from {message.player_id}")
            except Exception as e:
                self.logger.error(f"Failed to decrypt session key: {e}")
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        try:
            self.logger.info(f"Processing message type: {message.type}")
            print(f"DEBUG: Client received message type: {message.type}")
            
            if message.type == MessageType.JOIN:
                player_name = message.data.get('player_name', 'Unknown')
                player_id = message.player_id
                public_key = message.data.get('public_key')
                
                if public_key:
                    self.player_keys[player_id] = public_key
                    self.player_names[player_id] = player_name  # Store player name
                
                print(f"\n> {player_name} joined the game")
                
            elif message.type == MessageType.START_ROUND:
                print("\n> Round starting!")
                round_num = message.data.get('round_num', 1)
                self._round_active = True
                print(f"Debug: GameClient set round_active to {self._round_active}")
                
                # Add debug for handler call
                if MessageType.START_ROUND in self.handlers:
                    print("Debug: Calling START_ROUND handler")
                    await self.handlers[MessageType.START_ROUND](message)
                else:
                    print("Debug: No START_ROUND handler registered!")
                    
                print(f"> Round {round_num} is starting!")
                print("> Enter your bid (0-100):")
                
            elif message.type == MessageType.END_ROUND:
                print("\n=== Client: Processing END_ROUND ===")  # Added marker
                print(f"DEBUG: END_ROUND message data: {message.data}")
                if MessageType.END_ROUND in self.handlers:
                    print("DEBUG: Calling END_ROUND handler")
                    await self.handlers[MessageType.END_ROUND](message)
                else:
                    print("DEBUG: No END_ROUND handler registered!")
                round_num = message.data.get('round_num', 0)
                self._round_active = False
                print(f"DEBUG: Client finished processing END_ROUND")
                if 'results' in message.data:
                    for player, result in message.data['results'].items():
                        print(f"  {player}: {result}")
                
            elif message.type == MessageType.ERROR:
                print(f"\nServer Error: {message.data.get('error', 'Unknown error')}")
                
            self.logger.info(f"After handling message, round_active = {self._round_active}")
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            print(f"\nError processing message: {e}")
            
    def stop(self):
        """Stop the client"""
        self.running = False
        if self.writer:
            self.writer.close()
    
    async def close(self):
        """Close the connection"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def receive_messages(self):
        """Process incoming messages from the server"""
        try:
            while self.running:
                data = await self.reader.readline()
                if not data:
                    await asyncio.get_event_loop().run_in_executor(None, print, "\nLost connection to server")
                    break
                    
                try:
                    message_str = data.decode().strip()
                    self.logger.debug(f"Received raw message: {message_str}")
                    
                    message = Protocol.deserialize(message_str)
                    self.logger.info(f"Deserialized message type: {message.type}")
                    
                    await self.handle_message(message)
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Error decoding message: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    
        except asyncio.CancelledError:
            await asyncio.get_event_loop().run_in_executor(None, print, "\nMessage receiving cancelled")
        except Exception as e:
            self.logger.error(f"Error in receive_messages: {e}")
            await asyncio.get_event_loop().run_in_executor(None, print, f"\nError: {e}")
        finally:
            self.running = False
