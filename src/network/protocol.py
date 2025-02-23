import json
from typing import Optional
from .messages import Message, MessageType, JoinMessage, BidMessage, StartRoundMessage, EndRoundMessage, GameOverMessage, ErrorMessage, SessionKeyMessage

class Protocol:
    @staticmethod
    def serialize(message: Message) -> bytes:
        """Serialize a message to bytes"""
        data = {
            'type': message.type.name,
            'player_id': message.player_id,
            'data': message.data
        }
        # Ensure exactly one newline at the end
        return (json.dumps(data) + '\n').encode('utf-8')
        
    @staticmethod
    def deserialize(data: str) -> Message:
        """Deserialize a message from string"""
        try:
            # Remove any extra whitespace or newlines
            data = data.strip()
            if not data:
                raise ValueError("Empty message")
                
            parsed = json.loads(data)
            msg_type = MessageType[parsed['type']]
            player_id = parsed.get('player_id')
            data = parsed.get('data', {})
            
            # Create appropriate message type
            if msg_type == MessageType.JOIN:
                return JoinMessage(
                    player_id=player_id,
                    player_name=data.get('player_name', ''),
                    public_key=data.get('public_key', '')
                )
            elif msg_type == MessageType.BID:
                return BidMessage(data.get('encrypted_bids', {}))
            elif msg_type == MessageType.START_ROUND:
                return StartRoundMessage(data.get('round', 1))
            elif msg_type == MessageType.END_ROUND:
                return EndRoundMessage(data.get('round', 1), data.get('results', {}))
            elif msg_type == MessageType.GAME_OVER:
                return GameOverMessage(data.get('winners', []), data.get('scores', {}))
            elif msg_type == MessageType.ERROR:
                return ErrorMessage(data.get('error', ''))
            elif msg_type == MessageType.SESSION_KEY:
                return SessionKeyMessage(
                    data.get('target_id', ''),
                    data.get('encrypted_key', '')
                )
            else:
                raise ValueError(f"Unknown message type: {msg_type}")
                
        except Exception as e:
            raise ValueError(f"Error deserializing message: {e}")

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
