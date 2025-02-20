import json
from typing import Optional
from .messages import Message, MessageType, JoinMessage, BidMessage, StartRoundMessage, EndRoundMessage, GameOverMessage, ErrorMessage

class Protocol:
    @staticmethod
    def serialize(message: Message) -> bytes:
        """Serialize a message to bytes"""
        data = {
            'type': message.type.value,
            'player_id': message.player_id,
            'data': message.data,
            'round_num': message.round_num
        }
        return json.dumps(data).encode() + b'\n'

    @staticmethod
    def deserialize(data: bytes) -> Optional[Message]:
        """Deserialize bytes to a message"""
        try:
            message_dict = json.loads(data.decode().strip())
            msg_type = MessageType(message_dict['type'])
            player_id = message_dict['player_id']
            msg_data = message_dict['data']
            round_num = message_dict.get('round_num')

            if msg_type == MessageType.JOIN:
                return JoinMessage(player_id, msg_data['player_name'])
            elif msg_type == MessageType.BID:
                return BidMessage(player_id, round_num, msg_data['value'])
            elif msg_type == MessageType.START_ROUND:
                return StartRoundMessage(round_num)
            elif msg_type == MessageType.END_ROUND:
                return EndRoundMessage(round_num, msg_data['results'])
            elif msg_type == MessageType.GAME_OVER:
                return GameOverMessage(msg_data['final_scores'])
            elif msg_type == MessageType.ERROR:
                return ErrorMessage(msg_data['error'])
            else:
                return Message(msg_type, player_id, msg_data, round_num)
        except Exception as e:
            print(f"Error deserializing message: {e}")
            return None

    @staticmethod
    def validate_message(message: Message) -> Optional[str]:
        """Validate a message format"""
        if not message:
            return "Invalid message"
        if not isinstance(message.type, MessageType):
            return "Invalid message type"
        if not message.player_id:
            return "Missing player ID"
        if not isinstance(message.data, dict):
            return "Invalid message data format"
        return None
