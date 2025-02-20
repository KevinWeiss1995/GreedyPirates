import unittest
from src.core.player import Player

class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.player = Player("p1", "Blackbeard")

    def test_bid_placement(self):
        # Test valid bid
        self.assertTrue(self.player.place_bid(50))
        self.assertEqual(self.player.current_bid, 50)
        
        # Test invalid bid
        self.assertFalse(self.player.place_bid(-10))

    def test_gold_reception(self):
        initial_gold = self.player.total_gold
        self.player.receive_gold(30)
        self.assertEqual(self.player.total_gold, initial_gold + 30)

    def test_bid_reset(self):
        self.player.place_bid(50)
        self.player.reset_bid()
        self.assertIsNone(self.player.current_bid)

    def test_status(self):
        status = self.player.get_status()
        self.assertEqual(status["id"], "p1")
        self.assertEqual(status["name"], "Blackbeard")
        self.assertEqual(status["total_gold"], 0)
        self.assertFalse(status["has_bid"])
