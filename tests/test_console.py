import unittest
import asyncio
import aioconsole
from unittest.mock import patch, MagicMock, AsyncMock
from src.ui.console import ConsoleUI
from src.network.messages import (
    MessageType, Message, StartRoundMessage, EndRoundMessage, GameOverMessage
)

class TestConsoleUI(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.console = ConsoleUI()
        self.input_patcher = patch('aioconsole.ainput')
        self.mock_input = self.input_patcher.start()
        
    async def asyncTearDown(self):
        self.input_patcher.stop()
        if self.console.client:
            await self.console.client.close()
    
    async def test_start_and_join(self):
        self.mock_input.side_effect = ["TestPlayer", "", ""]
        
        with patch('src.network.client.GameClient.connect') as mock_connect, \
             patch('src.network.client.GameClient.join_game') as mock_join, \
             patch.object(self.console, 'input_loop') as mock_input_loop:
            
            mock_connect.return_value = True
            mock_join.return_value = True
            
            await self.console.start()
            
            mock_connect.assert_called_once()
            mock_join.assert_called_once()
            self.assertEqual(self.console.player_name, "TestPlayer")
    
    async def test_handle_commands(self):
        mock_client = AsyncMock()
        self.console.client = mock_client
        self.console.current_round = 1
        self.console.running = True
        
        await self.console.handle_command("bid 100")
        mock_client.send_bid.assert_called_once_with(1, {'value': 100})
        
        with patch('builtins.print') as mock_print:
            await self.console.handle_command("help")
            mock_print.assert_called()
        
        # Test invalid command separately
        with patch('builtins.print') as mock_print, \
             patch.object(self.console, 'show_help') as mock_show_help:
            await self.console.handle_command("invalid")
            mock_print.assert_called_with("Unknown command: invalid")
    
    async def test_message_handlers(self):
        with patch('builtins.print') as mock_print:
            await self.console.handle_start_round(StartRoundMessage(round_num=1))
            self.assertEqual(self.console.current_round, 1)
            
            results = {"player1": 100, "player2": 50}
            await self.console.handle_end_round(EndRoundMessage(round_num=1, results=results))
            
            scores = {"player1": 300, "player2": 200}
            await self.console.handle_game_over(GameOverMessage(final_scores=scores))
            self.assertFalse(self.console.running)

if __name__ == '__main__':
    unittest.main() 