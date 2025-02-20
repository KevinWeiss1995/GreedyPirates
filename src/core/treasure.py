from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class TreasureResult:
    total_bid: int
    payouts: Dict[str, int]
    valid_players: List[str]
    exceeded_limit: bool

class TreasureChest:
    def __init__(self, amount: int = 100):
        self.total_amount = amount

    def calculate_payouts(self, bids: Dict[str, int]) -> TreasureResult:
        """
        Calculate payouts based on player bids.
        
        Args:
            bids: Dictionary of player_id -> bid_amount
            
        Returns:
            TreasureResult containing payout information
        """
        total_bid = sum(bids.values())
        num_players = len(bids)
        
        # Initialize result
        payouts: Dict[str, int] = {}
        valid_players: List[str] = []
        
        if total_bid <= self.total_amount:
            # Everyone gets what they bid
            payouts = bids.copy()
            valid_players = list(bids.keys())
            exceeded_limit = False
        else:
            # Only players who didn't bid too high get paid
            fair_share = self.total_amount / num_players
            valid_players = [
                player_id 
                for player_id, bid in bids.items() 
                if bid <= fair_share
            ]
            
            if valid_players:
                # Split treasure among valid players
                share = self.total_amount / len(valid_players)
                for player_id in valid_players:
                    payouts[player_id] = int(share)
            
            exceeded_limit = True
            
        return TreasureResult(
            total_bid=total_bid,
            payouts=payouts,
            valid_players=valid_players,
            exceeded_limit=exceeded_limit
        )

    def validate_bid(self, bid: int) -> bool:
        """Validate if a bid is within acceptable range."""
        return 0 <= bid <= self.total_amount
