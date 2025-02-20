import unittest
from src.core.treasure import TreasureChest, TreasureResult

class TestTreasureChest(unittest.TestCase):
    def setUp(self):
        self.treasure = TreasureChest(100)

    def test_valid_distribution(self):
        bids = {
            "p1": 30,
            "p2": 40,
            "p3": 20
        }
        result = self.treasure.calculate_payouts(bids)
        self.assertEqual(result.total_bid, 90)
        self.assertEqual(result.payouts["p1"], 30)
        self.assertEqual(result.payouts["p2"], 40)
        self.assertEqual(result.payouts["p3"], 20)
        self.assertFalse(result.exceeded_limit)

    def test_greedy_distribution(self):
        bids = {
            "p1": 60,
            "p2": 50,
            "p3": 20
        }
        result = self.treasure.calculate_payouts(bids)
        self.assertEqual(result.total_bid, 130)
        self.assertTrue(result.exceeded_limit)
        self.assertNotIn("p1", result.payouts)
        self.assertNotIn("p2", result.payouts)
        self.assertIn("p3", result.payouts)

    def test_bid_validation(self):
        self.assertTrue(self.treasure.validate_bid(50))
        self.assertTrue(self.treasure.validate_bid(0))
        self.assertTrue(self.treasure.validate_bid(100))
        self.assertFalse(self.treasure.validate_bid(-1))
        self.assertFalse(self.treasure.validate_bid(101))