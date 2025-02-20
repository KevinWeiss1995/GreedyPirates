from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional

class MessageType(Enum):
    JOIN = 'join'
    BID = 'bid'
    START_ROUND = 'start_round'
    END_ROUND = 'end_round'
    GAME_OVER = 'game_over'
    ERROR = 'error'

@dataclass
class Message:
    type: MessageType
    player_id: str
    data: Dict[str, Any]
    round_num: Optional[int] = None

@dataclass
class JoinMessage(Message):
    def __init__(self, player_id: str, player_name: str):
        super().__init__(
            type=MessageType.JOIN,
            player_id=player_id,
            data={'player_name': player_name}
        )

@dataclass
class BidMessage(Message):
    def __init__(self, player_id: str, round_num: int, bid_value: int):
        super().__init__(
            type=MessageType.BID,
            player_id=player_id,
            round_num=round_num,
            data={'value': bid_value}
        )

@dataclass
class StartRoundMessage(Message):
    def __init__(self, round_num: int):
        super().__init__(
            type=MessageType.START_ROUND,
            player_id='server',
            round_num=round_num,
            data={}
        )

@dataclass
class EndRoundMessage(Message):
    def __init__(self, round_num: int, results: Dict[str, int]):
        super().__init__(
            type=MessageType.END_ROUND,
            player_id='server',
            round_num=round_num,
            data={'results': results}
        )

@dataclass
class GameOverMessage(Message):
    def __init__(self, final_scores: Dict[str, int]):
        super().__init__(
            type=MessageType.GAME_OVER,
            player_id='server',
            data={'final_scores': final_scores}
        )

@dataclass
class ErrorMessage(Message):
    def __init__(self, error_msg: str):
        super().__init__(
            type=MessageType.ERROR,
            player_id='server',
            data={'error': error_msg}
        )
