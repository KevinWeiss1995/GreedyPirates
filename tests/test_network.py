import unittest
import asyncio
import json
from src.network.messages import (
    Message, MessageType, JoinMessage, BidMessage, ShareMessage,
    StartRoundMessage, EndRoundMessage, GameOverMessage, ErrorMessage
)
from src.network.protocol import Protocol
from src.network.client import GameClient
from src.network.server import GameServer

class TestMessages(unittest.TestCase):
    def test_join_message(self):
        msg = JoinMessage(
            player_id="p1",
            player_name="Player 1",
            public_key="test_key"
        )
        self.assertEqual(msg.type, MessageType.JOIN)
        self.assertEqual(msg.player_id, "p1")
        self.assertEqual(msg.data["player_name"], "Player 1")
        self.assertEqual(msg.data["public_key"], "test_key")

    def test_bid_message(self):
        shares = {"p1": {"value": 10}, "p2": {"value": 20}}
        msg = BidMessage(
            player_id="p1",
            round_num=1,
            shares=shares
        )
        self.assertEqual(msg.type, MessageType.BID)
        self.assertEqual(msg.round_num, 1)
        self.assertEqual(msg.data["shares"], shares)

class TestProtocol(unittest.TestCase):
    def test_serialize_deserialize(self):
        original_msg = JoinMessage(
            player_id="p1",
            player_name="Player 1",
            public_key="test_key"
        )
        data = Protocol.serialize(original_msg)
        decoded_msg = Protocol.deserialize(data)
        self.assertEqual(decoded_msg.type, original_msg.type)
        self.assertEqual(decoded_msg.player_id, original_msg.player_id)
        self.assertEqual(decoded_msg.data, original_msg.data)

    def test_validate_message(self):
        valid_msg = JoinMessage(
            player_id="p1",
            player_name="Player 1",
            public_key="test_key"
        )
        self.assertIsNone(Protocol.validate_message(valid_msg))
        
        invalid_msg = Message(
            type=MessageType.JOIN,
            player_id="p1",
            data={}
        )
        self.assertIsNotNone(Protocol.validate_message(invalid_msg))

class TestNetworkIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create and start server
        self.server = GameServer(port=8889)
        self.server_task = asyncio.create_task(self.server.start())
        await asyncio.sleep(0.1)  # Allow server to start

    async def asyncTearDown(self):
        # Stop server and cancel task
        self.server.stop()
        self.server_task.cancel()
        try:
            await self.server_task
        except asyncio.CancelledError:
            pass

    async def test_basic_connection(self):
        # Create and connect a single client
        client = GameClient(port=8889)
        connected = await client.connect()
        self.assertTrue(connected)
        
        # Join game
        success = await client.join_game("p1", "Player 1")
        self.assertTrue(success)
        
        # Clean up
        client.stop()
        await client.close()

    async def test_message_exchange(self):
        # Create and connect client
        client = GameClient(port=8889)
        await client.connect()
        
        # Set up message received event
        message_received = asyncio.Event()
        
        async def handle_message(message):
            message_received.set()
            
        client.register_handler(MessageType.START_ROUND, handle_message)
        
        # Start message receiving task
        receive_task = asyncio.create_task(client.receive_messages())
        
        # Join game
        await client.join_game("p1", "Player 1")
        
        # Wait briefly for any server response
        try:
            await asyncio.wait_for(message_received.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass
        
        # Clean up
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
            
        client.stop()
        await client.close()

def run_async_test(coro):
    return asyncio.run(coro)

if __name__ == '__main__':
    unittest.main()
