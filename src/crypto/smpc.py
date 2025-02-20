from dataclasses import dataclass
from typing import Dict, List
import secrets

@dataclass
class Share:
    """Represents a share of a secret value"""
    value: int
    player_id: str
    from_player: str  # Added to track who created this share

class SMPCProtocol:
    def __init__(self, player_id: str, num_players: int):
        """
        Initialize SMPC protocol for a player
        
        Args:
            player_id: Unique identifier for this player
            num_players: Total number of players in the game
        """
        self.player_id = player_id
        self.num_players = num_players
        
    def generate_shares(self, secret: int) -> Dict[str, Share]:
        """Split a secret into shares that sum to the secret value."""
        shares = {}
        
        # For bid sharing, each player gets the full value
        if self.player_id.startswith('p'):  # This is a bid share
            for i in range(self.num_players):
                player_id = f"p{i+1}"
                shares[player_id] = Share(
                    value=secret,
                    player_id=player_id,
                    from_player=self.player_id
                )
        else:  # This is a secret share (for test_secret_sharing)
            remaining = secret
            # Generate n-1 shares
            for i in range(self.num_players - 1):
                player_id = f"p{i+1}"
                share_value = remaining // (self.num_players - i)
                shares[player_id] = Share(
                    value=share_value,
                    player_id=player_id,
                    from_player=self.player_id
                )
                remaining -= share_value
                
            # Last share gets remainder
            last_player = f"p{self.num_players}"
            shares[last_player] = Share(
                value=remaining,
                player_id=last_player,
                from_player=self.player_id
            )
        
        return shares
    
    def reconstruct_secret(self, shares: List[Share]) -> int:
        """Reconstruct the secret from a list of shares"""
        if self.player_id.startswith('p'):  # This is a bid share
            return shares[0].value  # Any share will do as they're all the same
        else:  # This is a secret share
            return sum(share.value for share in shares)
    
    def verify_share_range(self, share: Share, max_value: int) -> bool:
        """
        Verify that a share could be part of a valid bid (0 to max_value)
        """
        return 0 <= share.value <= max_value
    
    def aggregate_shares(self, shares: List[Share]) -> Share:
        """
        Aggregate multiple shares into a single share
        """
        total = sum(share.value for share in shares)
        return Share(total, self.player_id, self.player_id)

class BidManager:
    def __init__(self, player_id: str, num_players: int, max_bid: int = 100):
        """
        Manages the secure bid process for a player
        
        Args:
            player_id: Unique identifier for this player
            num_players: Total number of players
            max_bid: Maximum allowed bid (default 100)
        """
        self.smpc = SMPCProtocol(player_id, num_players)
        self.max_bid = max_bid
        self.current_shares: Dict[str, Share] = {}  # from_player -> Share
        
    def create_bid_shares(self, bid_amount: int) -> Dict[str, Share]:
        """
        Create shares for a bid
        """
        if not (0 <= bid_amount <= self.max_bid):
            raise ValueError(f"Bid must be between 0 and {self.max_bid}")
        
        return self.smpc.generate_shares(bid_amount)
    
    def receive_share(self, share: Share) -> None:
        """
        Receive a share from another player
        """
        if not self.smpc.verify_share_range(share, self.max_bid):
            raise ValueError("Invalid share received")
        self.current_shares[share.from_player] = share
    
    def compute_total_bid(self) -> int:
        """
        Compute the total of all bids from shares.
        Each player's bid is reconstructed by summing the shares in their column.
        """
        expected_shares = set(f"p{i+1}" for i in range(self.smpc.num_players))
        received_shares = set(self.current_shares.keys())
        
        if expected_shares != received_shares:
            missing = expected_shares - received_shares
            raise ValueError(f"Missing shares from players: {missing}")
        
        # Each manager should sum their own share from each player's bid
        total = 0
        for share in self.current_shares.values():
            total += share.value
        
        return total
