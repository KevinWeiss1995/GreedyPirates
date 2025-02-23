from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from dataclasses import dataclass
import os
import base64

class EncryptionError(Exception):
    pass

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
        self.keypair = None
        self.peer_keys = {}
        
    def generate_keypair(self):
        """Generate a new RSA keypair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.keypair = private_key
        
    def get_public_key_string(self) -> str:
        """Get public key as PEM string"""
        if not self.keypair:
            raise ValueError("No keypair generated")
            
        public_key = self.keypair.public_key()
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')
        
    def encrypt(self, data: bytes, public_key_pem: str) -> bytes:
        """Encrypt data using a public key"""
        try:
            # Convert PEM string to public key object
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            
            # Encrypt the data
            encrypted = public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return base64.b64encode(encrypted)
            
        except Exception as e:
            raise EncryptionError(f"Failed to encrypt: {e}")
            
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using private key"""
        try:
            # Decode base64 and decrypt
            encrypted = base64.b64decode(encrypted_data)
            
            decrypted = self.keypair.decrypt(
                encrypted,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return decrypted
            
        except Exception as e:
            raise EncryptionError(f"Failed to decrypt: {e}")
            
    def load_peer_key(self, peer_id: str, public_key_pem: str):
        """Store a peer's public key"""
        try:
            # Validate the key format before storing
            serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            self.peer_keys[peer_id] = public_key_pem
            print(f"Debug: Stored valid PEM key for {peer_id}")
        except Exception as e:
            print(f"Debug: Invalid key format from {peer_id}: {e}")
            raise
    
    def encrypt_for_peer(self, player_id: str, data: bytes) -> bytes:
        """Encrypt data for a specific peer"""
        if player_id not in self.peer_keys:
            raise ValueError(f"No public key found for player {player_id}")
            
        peer_key = self.peer_keys[player_id]
        encrypted = serialization.load_pem_public_key(
            peer_key.encode('utf-8'),
            backend=default_backend()
        ).encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(encrypted)
    
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
