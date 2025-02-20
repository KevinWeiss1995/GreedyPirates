from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from dataclasses import dataclass
import os
import base64

@dataclass
class KeyPair:
    public_key: rsa.RSAPublicKey
    private_key: rsa.RSAPrivateKey
    
    def public_bytes(self) -> bytes:
        """Get the public key in PEM format"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def public_str(self) -> str:
        """Get the public key as a base64 string"""
        return base64.b64encode(self.public_bytes()).decode('utf-8')

class KeyManager:
    def __init__(self):
        self.keypair: KeyPair = None
        self.peer_keys: dict[str, rsa.RSAPublicKey] = {}
        
    def generate_keypair(self, key_size: int = 2048) -> KeyPair:
        """Generate a new RSA keypair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        self.keypair = KeyPair(public_key, private_key)
        return self.keypair
    
    def load_peer_key(self, player_id: str, key_data: str) -> None:
        """Load a peer's public key from base64 string"""
        key_bytes = base64.b64decode(key_data)
        public_key = serialization.load_pem_public_key(
            key_bytes,
            backend=default_backend()
        )
        self.peer_keys[player_id] = public_key
    
    def encrypt_for_peer(self, player_id: str, data: bytes) -> bytes:
        """Encrypt data for a specific peer"""
        if player_id not in self.peer_keys:
            raise ValueError(f"No public key found for player {player_id}")
            
        peer_key = self.peer_keys[player_id]
        encrypted = peer_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return encrypted
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using our private key"""
        if not self.keypair:
            raise ValueError("No keypair loaded")
            
        decrypted = self.keypair.private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted
    
    def generate_session_key(self) -> bytes:
        """Generate a random session key for symmetric encryption"""
        return os.urandom(32)  # 256-bit key
    
    def encrypt_session_key(self, session_key: bytes, player_id: str) -> bytes:
        """Encrypt a session key for a specific peer"""
        return self.encrypt_for_peer(player_id, session_key)
    
    def decrypt_session_key(self, encrypted_session_key: bytes) -> bytes:
        """Decrypt a session key"""
        return self.decrypt(encrypted_session_key)
    
    @staticmethod
    def encrypt_with_session_key(session_key: bytes, data: bytes) -> bytes:
        """Encrypt data using a session key"""
        iv = os.urandom(16)  # Generate random IV
        cipher = Cipher(
            algorithms.AES(session_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Add PKCS7 padding
        padding_length = 16 - (len(data) % 16)
        padded_data = data + bytes([padding_length] * padding_length)
        
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return iv + encrypted  # Prepend IV to encrypted data
    
    @staticmethod
    def decrypt_with_session_key(session_key: bytes, encrypted_data: bytes) -> bytes:
        """Decrypt data using a session key"""
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        cipher = Cipher(
            algorithms.AES(session_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]  # Remove padding
