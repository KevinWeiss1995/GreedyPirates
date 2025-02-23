from typing import Dict, List, Optional
from .player import Player
from .treasure import TreasureChest
from src.crypto.smpc import BidManager, Share
import logging

class BidVerificationError(Exception):
    """Error during bid verification"""
    pass

class GameState:
    TREASURE_AMOUNT = 100  # Total treasure to bid on each round
    
    def __init__(self, min_players: int = 3, max_players: int = 6, max_rounds: int = 10):
        self.min_players = min_players
        self.max_players = max_players
        self.max_rounds = max_rounds
        self.players = []
        self.scores: Dict[str, int] = {}   # player_id -> total score
        self.bids = {}  # player_id -> encrypted_bids
        self.current_round = 0  # Will be set to 1 when first round starts
        self.round_active = False
        self.treasure_amount = self.TREASURE_AMOUNT  # Default treasure amount per round
        self.treasure = TreasureChest(self.TREASURE_AMOUNT)
        self.bid_manager: Optional[BidManager] = None
        self.received_shares: Dict[str, Dict[str, Share]] = {}  # player_id -> {from_player_id -> Share}
        self.game_complete: bool = False
        self.logger = logging.getLogger('game_state')
        self.encrypted_bids = {}
        self.decrypted_bids = {}
        
    def add_player(self, player_id: str, player_name: str) -> None:
        """Add a player to the game"""
        self.players.append(player_id)
        self.scores[player_id] = 0
       
        if len(self.players) >= self.min_players and self.current_round == 0:
            self.start_round()
    
    def remove_player(self, player_id: str) -> None:
        """Remove a player from the game"""
        if player_id in self.players:
            self.players.remove(player_id)
        if player_id in self.scores:
            del self.scores[player_id]
        if player_id in self.bids:
            del self.bids[player_id]
    
    def start_round(self) -> None:
        """Start a new round"""
        if not self.players:
            raise ValueError("Cannot start round - no players")
            
        if len(self.players) < self.min_players:
            raise ValueError(f"Need at least {self.min_players} players to start")
            
        self.current_round += 1
        self.round_active = True
        self.bids.clear()
        self.encrypted_bids.clear() 
        self.decrypted_bids.clear() 
        
        self.logger.info(f"Starting round {self.current_round}")
        
        self.received_shares = {pid: {} for pid in self.players}
        self.treasure_amount = self.TREASURE_AMOUNT  # Reset treasure amount for new round
    
    def reset_round(self):
        """Reset the round state"""
        self.bids.clear()
        self.round_active = False
        print(f"Reset round state")
    
    def place_bid(self, player_id: str, bid_data: dict):
        """Place a bid for a player"""
        if not self.round_active:
            raise ValueError("Cannot bid - round not active")
            
        if player_id not in self.players:
            raise ValueError(f"Unknown player {player_id}")
            
        if player_id in self.bids:
            raise ValueError(f"Player {player_id} already bid this round")
            
        # Store the encrypted bid data directly
        self.bids[player_id] = bid_data
    
    def all_bids_placed(self) -> bool:
        """Check if all players have placed bids"""
        return len(self.bids) == len(self.players)
    
    def calculate_results(self) -> dict:
        """Calculate round results"""
        # For now, just return the encrypted bids
        # Actual bid comparison will happen after decryption
        return {
            player: "bid_placed" 
            for player in self.bids.keys()
        }
    
    def calculate_round_results(self) -> Dict[str, Dict[str, int]]:
        """Calculate the results for the current round"""
        print(f"DEBUG: Calculating results with bids: {self.bids}")  # Debug print
        
        total_bids = sum(int(bid) for bid in self.bids.values())
        results = {}
        
        if total_bids == 0:  # Prevent division by zero
            # If no one bids, split treasure equally
            share = self.treasure_amount // len(self.players)
            for player_id in self.players:
                results[player_id] = {
                    'name': player_id,
                    'bid': self.bids.get(player_id, 0),
                    'share': share
                }
        else:
            # Calculate proportional shares
            for player_id, bid in self.bids.items():
                share = (int(bid) * self.treasure_amount) // total_bids
                results[player_id] = {
                    'name': player_id,
                    'bid': bid,
                    'share': share
                }
                self.scores[player_id] += share
                
        print(f"DEBUG: Calculated results: {results}")  # Debug print
        self.round_active = False
        return results
    
    def is_game_over(self) -> bool:
        """Check if the game is over"""
        return self.current_round >= self.max_rounds
    
    def get_final_scores(self) -> Dict[str, int]:
        """Get the final scores"""
        return self.scores.copy()
    
    def initialize_bid_manager(self, player_id: str):
        """Initialize SMPC bid manager for this player."""
        self.bid_manager = BidManager(player_id, len(self.players))
        self.received_shares = {pid: {} for pid in self.players}
    
    def receive_share(self, from_player: str, to_player: str, share: Share) -> None:
        """Receive a share of a bid from another player."""
        if not self.round_active:
            return
        
        self.received_shares[to_player][from_player] = share
        if self.bid_manager and self.bid_manager.smpc.player_id == to_player:
            self.bid_manager.receive_share(share)
    
    def all_shares_received(self, player_id: str) -> bool:
        """Check if all shares have been received for a player."""
        return len(self.received_shares[player_id]) == len(self.players)
    
    def calculate_round_results_smpc(self) -> Dict:
        """Calculate the results of the current round using SMPC."""
        if not self.round_active or not self.all_bids_placed():
            return {}
            
        try:
            # Get all bids (for now, using direct bids for testing)
            bids = {player_id: player.current_bid 
                    for player_id, player in self.players.items()}
            
            # Use treasure chest to calculate payouts
            result = self.treasure.calculate_payouts(bids)
            
            return {
                "total_bid": result.total_bid,
                "payouts": result.payouts,
                "exceeded_limit": result.exceeded_limit
            }
        except ValueError as e:
            print(f"Error calculating results: {e}")
            return {}
    
    def end_round(self) -> Dict:
        """End the current round and distribute gold."""
        if not self.round_active or not self.all_bids_placed():
            return {}
        
        results = self.calculate_round_results_smpc()
        if not results:
            return {}
            
        # Distribute gold
        for player_id, payout in results["payouts"].items():
            self.players[player_id].receive_gold(payout)
        
        self.round_active = False
        
        # Update game completion status
        if self.current_round >= self.max_rounds:
            self.game_complete = True
        
        return results
    
    def get_game_status(self) -> Dict:
        """Get the current game status."""
        return {
            "current_round": self.current_round,
            "total_rounds": self.max_rounds,
            "round_active": self.round_active,
            "players": {
                player_id: player.get_status()
                for player_id, player in self.players.items()
            },
            "game_complete": self.current_round >= self.max_rounds
        }
    
    def place_encrypted_bid(self, player_id: str, encrypted_bids: Dict[str, str]) -> None:
        """Place encrypted bids for a player"""
        if not self.round_active:
            raise ValueError("Round not active")
        if player_id not in self.players:
            raise ValueError("Player not in game")
            
        # Store encrypted bids for later processing
        if not hasattr(self, 'encrypted_bids'):
            self.encrypted_bids = {}
        self.encrypted_bids[player_id] = encrypted_bids
        
    def verify_bid_consistency(self, player_id: str) -> Optional[int]:
        """Verify that all decrypted copies of a bid match"""
        if player_id not in self.decrypted_bids:
            return None
            
        bid_values = set(self.decrypted_bids[player_id].values())
        
        if not bid_values:
            raise BidVerificationError(f"No decrypted bids found for {player_id}")
            
        if len(bid_values) > 1:
            # Log the inconsistent values for debugging
            self.logger.error(f"Inconsistent bids from {player_id}: {self.decrypted_bids[player_id]}")
            raise BidVerificationError(f"Player {player_id} submitted inconsistent bids")
            
        bid_value = bid_values.pop()
        if not isinstance(bid_value, int) or bid_value < 0:
            raise BidVerificationError(f"Invalid bid value from {player_id}: {bid_value}")
            
        return bid_value
        
    def process_decrypted_bid(self, from_player: str, for_player: str, bid_value: int) -> None:
        """Process a decrypted bid value with verification"""
        try:
            if not self.round_active:
                raise ValueError("Round not active")
                
            if from_player not in self.players or for_player not in self.players:
                raise ValueError("Invalid player ID")
                
            if not isinstance(bid_value, int) or bid_value < 0:
                raise ValueError("Invalid bid value")
                
            # Store decrypted bid
            if not hasattr(self, 'decrypted_bids'):
                self.decrypted_bids = {}
            if from_player not in self.decrypted_bids:
                self.decrypted_bids[from_player] = {}
                
            self.decrypted_bids[from_player][for_player] = bid_value
            
            # Check if we have all decrypted bids for this player
            if len(self.decrypted_bids[from_player]) == len(self.players) - 1:
                verified_bid = self.verify_bid_consistency(from_player)
                if verified_bid is not None:
                    self.bids[from_player] = verified_bid
                    self.logger.info(f"Verified bid from {from_player}: {verified_bid}")
                    
        except Exception as e:
            self.logger.error(f"Error processing bid: {e}")
            raise