from dataclasses import dataclass
from typing import Optional

@dataclass
class Player:
    id: str
    name: str
    total_gold: int = 0
    current_bid: Optional[int] = None
    
    def place_bid(self, amount: int) -> bool:
        """Place a bid for the current round."""
        if amount < 0:
            return False
        self.current_bid = amount
        return True
    
    def receive_gold(self, amount: int) -> None:
        """Receive gold from a round's payout."""
        self.total_gold += amount
        
    def reset_bid(self) -> None:
        """Reset bid for the next round."""
        self.current_bid = None
    
    def get_status(self) -> dict:
        """Get player's current status."""
        return {
            "id": self.id,
            "name": self.name,
            "total_gold": self.total_gold,
            "has_bid": self.current_bid is not None
        }
