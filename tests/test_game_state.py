import unittest
from src.core.game_state import GameState

class TestGameState(unittest.TestCase):
    def setUp(self):
        self.game = GameState()
        # Add three test players
        self.game.add_player("p1", "Blackbeard")
        self.game.add_player("p2", "Anne Bonny")
        self.game.add_player("p3", "Captain Kidd")

    def test_smpc_round_flow(self):
        # Start round
        self.assertTrue(self.game.start_round())
        
        # Initialize bid managers for each player
        self.game.initialize_bid_manager("p1")
        
        # Place bids and distribute shares
        shares1 = self.game.place_bid("p1", 30)
        shares2 = self.game.place_bid("p2", 40)
        shares3 = self.game.place_bid("p3", 20)
        
        # Distribute shares
        for pid, share in shares1.items():
            self.game.receive_share("p1", pid, share)
        for pid, share in shares2.items():
            self.game.receive_share("p2", pid, share)
        for pid, share in shares3.items():
            self.game.receive_share("p3", pid, share)
        
        # Calculate results
        results = self.game.end_round()
        
        # Verify results
        self.assertIn("total_bid", results)
        self.assertEqual(results["total_bid"], 90)
        self.assertEqual(results["payouts"]["p1"], 30)
        self.assertEqual(results["payouts"]["p2"], 40)
        self.assertEqual(results["payouts"]["p3"], 20)

    def test_greedy_bids(self):
        self.game.start_round()
        
        # Place greedy bids
        self.game.place_bid("p1", 60)
        self.game.place_bid("p2", 50)
        self.game.place_bid("p3", 20)
        
        results = self.game.end_round()
        # Total bid (130) exceeds treasure (100)
        self.assertEqual(results["total_bid"], 130)
        # Only p3 should get a payout (as they bid conservatively)
        self.assertNotIn("p1", results["payouts"])
        self.assertNotIn("p2", results["payouts"])
        self.assertIn("p3", results["payouts"])

    def test_game_completion(self):
        """Test that the game completes after 5 rounds"""
        for _ in range(self.game.TOTAL_ROUNDS):
            self.game.start_round()
            # Place conservative bids
            self.game.place_bid("p1", 20)
            self.game.place_bid("p2", 20)
            self.game.place_bid("p3", 20)
            
            # Distribute shares for each bid
            for pid in ["p1", "p2", "p3"]:
                shares = self.game.place_bid(pid, 20)
                for target_pid, share in shares.items():
                    self.game.receive_share(pid, target_pid, share)
                    
            self.game.end_round()
        
        # Try to start 6th round
        self.assertFalse(self.game.start_round())
        self.assertTrue(self.game.get_game_status()["game_complete"])
