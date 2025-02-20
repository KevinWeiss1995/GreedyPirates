import unittest
from src.crypto.keys import KeyManager
import base64

class TestKeyManager(unittest.TestCase):
    def setUp(self):
        self.km1 = KeyManager()
        self.km2 = KeyManager()
        
        # Generate keypairs for both managers
        self.km1.generate_keypair()
        self.km2.generate_keypair()
        
        # Exchange public keys
        self.km1.load_peer_key("p2", self.km2.keypair.public_str())
        self.km2.load_peer_key("p1", self.km1.keypair.public_str())
    
    def test_key_exchange(self):
        # Test basic encryption/decryption
        message = b"Hello, World!"
        encrypted = self.km1.encrypt_for_peer("p2", message)
        decrypted = self.km2.decrypt(encrypted)
        self.assertEqual(message, decrypted)
    
    def test_session_key(self):
        # Generate and exchange session key
        session_key = self.km1.generate_session_key()
        encrypted_session_key = self.km1.encrypt_session_key(session_key, "p2")
        decrypted_session_key = self.km2.decrypt_session_key(encrypted_session_key)
        self.assertEqual(session_key, decrypted_session_key)
        
        # Test session key encryption
        message = b"Secret message"
        encrypted = KeyManager.encrypt_with_session_key(session_key, message)
        decrypted = KeyManager.decrypt_with_session_key(session_key, encrypted)
        self.assertEqual(message, decrypted)
    
    def test_invalid_peer(self):
        with self.assertRaises(ValueError):
            self.km1.encrypt_for_peer("p3", b"test")
    
    def test_missing_keypair(self):
        km = KeyManager()
        with self.assertRaises(ValueError):
            km.decrypt(b"test")