import unittest
import asyncio
from src.network.client import GameClient
from src.network.server import GameServer
from src.network.messages import (
    MessageType, JoinMessage, BidMessage, StartRoundMessage
)

class TestServerIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Start server on a different port to avoid conflicts
        self.server = GameServer(port=8890)
        self.server_task = asyncio.create_task(self.server.start())
        await asyncio.sleep(0.1)  # Give server time to start
        
        # Create three test clients
        self.clients = []
        for i in range(3):
            client = GameClient(port=8890)
            await client.connect()
            self.clients.append(client)
    
    async def asyncTearDown(self):
        # Clean up clients
        for client in self.clients:
            client.stop()
            await client.close()
        
        # Clean up server
        self.server.stop()
        self.server_task.cancel()
        try:
            await self.server_task
        except asyncio.CancelledError:
            pass
    
    async def test_game_flow(self):
        # Track received messages
        start_round_received = asyncio.Event()
        
        # Message handler for clients
        async def handle_start_round(message):
            if message.type == MessageType.START_ROUND:
                start_round_received.set()
        
        # Register handler for all clients
        for client in self.clients:
            client.register_handler(MessageType.START_ROUND, handle_start_round)
        
        # Start message receiving for all clients
        receive_tasks = []
        for client in self.clients:
            task = asyncio.create_task(client.receive_messages())
            receive_tasks.append(task)
        
        # Join game with all clients
        for i, client in enumerate(self.clients):
            success = await client.join_game(
                player_id=f"p{i+1}",
                player_name=f"Player {i+1}"
            )
            self.assertTrue(success)
            await asyncio.sleep(0.1)  # Give time for server to process
        
        # Wait for start round message
        try:
            await asyncio.wait_for(start_round_received.wait(), timeout=2.0)
            self.assertTrue(start_round_received.is_set())
        except asyncio.TimeoutError:
            self.fail("Did not receive START_ROUND message")
        
        # Test bid submission
        await self.clients[0].send_bid(round_num=1, bid_value=10)
        
        # Give time for server to process
        await asyncio.sleep(0.1)
        
        # Verify server state
        self.assertTrue(self.server.game_state.round_active)
        
        # Clean up receive tasks
        for task in receive_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    async def test_server_capacity(self):
        # Try to connect a fourth client (should still work but not start game)
        extra_client = GameClient(port=8890)
        await extra_client.connect()
        
        success = await extra_client.join_game("p4", "Player 4")
        self.assertTrue(success)
        
        # Clean up extra client
        extra_client.stop()
        await extra_client.close()
    
    async def test_server_error_handling(self):
        # Test invalid message handling
        client = self.clients[0]
        await client.join_game("p1", "Player 1")
        
        # Try to send bid without active round
        await client.send_bid(round_num=999, bid_value=10)
        
        # Give time for server to process
        await asyncio.sleep(0.1)
        
        # Server should still be running
        self.assertTrue(self.server.running)

def run_async_test(coro):
    return asyncio.run(coro)

if __name__ == '__main__':
    unittest.main() 