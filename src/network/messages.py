from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Any, Optional
import json
import base64

class MessageType(Enum):
    JOIN = auto()
    BID = auto()
    START_ROUND = auto()
    END_ROUND = auto()
    GAME_OVER = auto()
    ERROR = auto()
    SESSION_KEY = auto()  # New message type for key exchange

@dataclass
class Message:
    type: MessageType
    player_id: str
    data: Dict[str, Any]
    round_num: Optional[int] = None

@dataclass
class JoinMessage(Message):
    def __init__(self, player_id: str, player_name: str, public_key: str):
        super().__init__(
            MessageType.JOIN,
            player_id,
            {
                'player_name': player_name,
                'public_key': public_key
            }
        )

@dataclass
class BidMessage(Message):
    def __init__(self, encrypted_bids: Dict[str, str]):
        super().__init__(
            MessageType.BID,
            None,
            {'encrypted_bids': encrypted_bids}
        )

@dataclass
class StartRoundMessage(Message):
    def __init__(self, round_num: int):
        super().__init__(
            MessageType.START_ROUND,
            'server',
            round_num=round_num,
            data={}
        )

@dataclass
class EndRoundMessage(Message):
    def __init__(self, round_num: int, results: Dict[str, int]):
        super().__init__(
            MessageType.END_ROUND,
            'server',
            round_num=round_num,
            data={'results': results}
        )

@dataclass
class GameOverMessage(Message):
    def __init__(self, final_scores: Dict[str, int]):
        super().__init__(
            MessageType.GAME_OVER,
            'server',
            data={'final_scores': final_scores}
        )

@dataclass
class ErrorMessage(Message):
    def __init__(self, error_msg: str):
        super().__init__(
            MessageType.ERROR,
            'server',
            data={'error': error_msg}
        )

@dataclass
class SessionKeyMessage(Message):
    def __init__(self, target_id: str, encrypted_key: str):
        super().__init__(
            MessageType.SESSION_KEY,
            None,
            {
                'target_id': target_id,
                'encrypted_key': encrypted_key
            }
        )
