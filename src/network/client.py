import asyncio
import uuid
import socket
from typing import Dict, Optional, Callable, Any
from asyncio import StreamReader, StreamWriter
from .protocol import Protocol
from .messages import Message, MessageType, JoinMessage, BidMessage
from ..crypto.keys import KeyManager
from ..utils.config import Config
from ..utils.logger import GameLogger

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
        
    def register_handler(self, msg_type: MessageType, handler: Callable[[Message], None]):
        """Register a handler for a specific message type"""
        self.handlers[msg_type] = handler
    
    async def connect(self, player_name: str) -> bool:
        """Connect to the game server"""
        try:
            print(f"\nAttempting connection to {self.host}:{self.port}")
            print("Connection details:")
            print(f"  Host: {self.host}")
            print(f"  Port: {self.port}")
            
            # Try localhost first if no host specified
            if not self.host:
                print("No host specified, trying localhost")
                self.host = 'localhost'
            
            # Handle IPv6 address
            if ':' in self.host:
                print("IPv6 address detected")
                self.host = self.host.strip('[]')
                print(f"Formatted IPv6 address: {self.host}")
            
            print("\nResolving address...")
            try:
                addrinfo = socket.getaddrinfo(
                    self.host,
                    self.port,
                    socket.AF_UNSPEC,  # Try both IPv4 and IPv6
                    socket.SOCK_STREAM
                )
                print(f"Address resolved: {addrinfo}")
            except socket.gaierror as e:
                print(f"Failed to resolve address: {e}")
                return False
            
            print("\nAttempting connection...")
            try:
                self.reader, self.writer = await asyncio.wait_for(
                    asyncio.open_connection(
                        host=self.host,
                        port=self.port
                    ),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                print("Connection timed out after 5 seconds")
                return False
            
            print("Connection established!")
            
            # Send join message
            join_msg = JoinMessage(self.player_id, player_name)
            await self.send_message(join_msg)
            
            self.running = True
            return True
            
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            print(f"\nDetailed connection error: {str(e)}")
            print(f"Error type: {type(e)}")
            return False
    
    async def send_message(self, message: Message):
        """Send a message to the server"""
        if not self.writer:
            raise ConnectionError("Not connected to server")
            
        data = Protocol.serialize(message)
        self.writer.write(data + b'\n')
        await self.writer.drain()
    
    async def send_bid(self, round_num: int, bid_value: int):
        """Send a bid to the server"""
        try:
            # Convert bid_value to int if it's a string
            bid_amount = int(bid_value) if isinstance(bid_value, str) else bid_value
            print(f"Sending bid of {bid_amount} for round {round_num}")
            
            bid_msg = BidMessage(
                player_id=self.player_id,
                round_num=round_num,
                bid_value=bid_amount
            )
            await self.send_message(bid_msg)
            print("Bid sent to server")
        except ValueError as e:
            print(f"Invalid bid value: {e}")
        except Exception as e:
            print(f"Error sending bid: {e}")
    
    async def receive_messages(self):
        """Main message receiving loop"""
        self.running = True
        
        while self.running:
            try:
                if not self.reader:
                    break
                    
                data = await self.reader.readline()
                if not data:
                    break
                    
                message = Protocol.deserialize(data)
                
                # Validate message
                error = Protocol.validate_message(message)
                if error:
                    print(f"Received invalid message: {error}")
                    continue
                
                # Handle message based on type
                if message.type in self.handlers:
                    handler = self.handlers[message.type]
                    try:
                        await handler(message)
                    except Exception as e:
                        print(f"Error in message handler: {e}")
                else:
                    print(f"No handler for message type: {message.type}")
                    
            except Exception as e:
                print(f"Error receiving message: {e}")
                if not self.running:
                    break
    
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
