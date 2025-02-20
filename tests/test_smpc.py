import unittest
from src.crypto.smpc import SMPCProtocol, BidManager, Share

class TestSMPC(unittest.TestCase):
    def setUp(self):
        self.num_players = 3
        self.smpc_p1 = SMPCProtocol("p1", self.num_players)
        self.smpc_p2 = SMPCProtocol("p2", self.num_players)
        self.smpc_p3 = SMPCProtocol("p3", self.num_players)

    def test_secret_sharing(self):
        # Test that we can share and reconstruct a secret
        secret = 50
        shares = self.smpc_p1.generate_shares(secret)
        
        # Verify we get the right number of shares
        self.assertEqual(len(shares), self.num_players)
        
        # Verify we can reconstruct the secret
        reconstructed = self.smpc_p1.reconstruct_secret(list(shares.values()))
        self.assertEqual(secret, reconstructed)

class TestBidManager(unittest.TestCase):
    def setUp(self):
        self.num_players = 3
        self.bid_manager_1 = BidManager("p1", self.num_players)
        self.bid_manager_2 = BidManager("p2", self.num_players)
        self.bid_manager_3 = BidManager("p3", self.num_players)

    def test_bid_sharing(self):
        # Each player creates their bid shares
        shares1 = self.bid_manager_1.create_bid_shares(30)  # p1 bids 30
        shares2 = self.bid_manager_2.create_bid_shares(40)  # p2 bids 40
        shares3 = self.bid_manager_3.create_bid_shares(20)  # p3 bids 20

        print("\nDebug shares:")
        print(f"Shares1 (bid=30): {[s.value for s in shares1.values()]}")
        print(f"Shares2 (bid=40): {[s.value for s in shares2.values()]}")
        print(f"Shares3 (bid=20): {[s.value for s in shares3.values()]}")

        # Each player receives a share from each bid
        for manager in [self.bid_manager_1, self.bid_manager_2, self.bid_manager_3]:
            manager.receive_share(shares1[manager.smpc.player_id])
            manager.receive_share(shares2[manager.smpc.player_id])
            manager.receive_share(shares3[manager.smpc.player_id])

        print("\nDebug received shares:")
        print(f"Manager1 shares: {[s.value for s in self.bid_manager_1.current_shares.values()]}")
        print(f"Manager2 shares: {[s.value for s in self.bid_manager_2.current_shares.values()]}")
        print(f"Manager3 shares: {[s.value for s in self.bid_manager_3.current_shares.values()]}")

        # Verify all managers compute the same total
        expected_total = 90  # 30 + 40 + 20
        total1 = self.bid_manager_1.compute_total_bid()
        total2 = self.bid_manager_2.compute_total_bid()
        total3 = self.bid_manager_3.compute_total_bid()

        print(f"\nDebug totals: {total1}, {total2}, {total3} (expected: {expected_total})")

        self.assertEqual(total1, expected_total)
        self.assertEqual(total2, expected_total)
        self.assertEqual(total3, expected_total)

    def test_invalid_bid(self):
        with self.assertRaises(ValueError):
            self.bid_manager_1.create_bid_shares(101)  # Above max
        with self.assertRaises(ValueError):
            self.bid_manager_1.create_bid_shares(-1)   # Below min
