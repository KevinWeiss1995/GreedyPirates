import unittest
import json
from pathlib import Path
from src.utils.config import Config

class TestConfig(unittest.TestCase):
    def setUp(self):
        # Use a test config directory
        self.test_config_dir = Path("test_config")
        self.config = Config(config_dir=str(self.test_config_dir))
        
    def tearDown(self):
        # Clean up test config files
        if self.test_config_dir.exists():
            for file in self.test_config_dir.glob("*.json"):
                file.unlink()
            self.test_config_dir.rmdir()
    
    def test_default_config_creation(self):
        """Test that default config files are created if none exist"""
        self.assertTrue(self.test_config_dir.exists())
        self.assertTrue((self.test_config_dir / "game_settings.json").exists())
        self.assertTrue((self.test_config_dir / "network.json").exists())
    
    def test_config_loading(self):
        """Test loading config values"""
        # Test default values
        self.assertEqual(self.config.get("server", "port"), 8888)
        self.assertEqual(self.config.get("game", "min_players"), 3)
        
        # Test custom config
        custom_config = {
            "game": {
                "min_players": 4,
                "treasure_amount": 200
            }
        }
        
        config_path = self.test_config_dir / "game_settings.json"
        with open(config_path, 'w') as f:
            json.dump(custom_config, f)
            
        # Create new config instance to load new values
        new_config = Config(config_dir=str(self.test_config_dir))
        self.assertEqual(new_config.get("game", "min_players"), 4)
        self.assertEqual(new_config.get("game", "treasure_amount"), 200)
    
    def test_config_setting(self):
        """Test setting config values"""
        self.config.set("game", "new_setting", "test_value")
        self.assertEqual(self.config.get("game", "new_setting"), "test_value")
    
    def test_missing_values(self):
        """Test handling of missing config values"""
        self.assertIsNone(self.config.get("nonexistent", "key"))
        self.assertIsNone(self.config.get("game", "nonexistent_key"))

if __name__ == '__main__':
    unittest.main() 