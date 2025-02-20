import json
from pathlib import Path
from typing import Dict, Any

class Config:
    DEFAULT_CONFIG = {
        "server": {
            "host": "localhost",
            "port": 8888,
            "reconnect_attempts": 3,
            "timeout": 5
        },
        "game": {
            "min_players": 3,
            "max_players": 8,
            "max_rounds": 10,
            "treasure_amount": 100,
            "bid_timeout": 30,
            "round_timeout": 60
        }
    }
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_all_configs()
    
    def load_all_configs(self) -> None:
        """Load and merge all config files"""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)
            self.save_default_configs()
            return
            
        self.load_config_file("game_settings.json")
        self.load_config_file("network.json")
    
    def load_config_file(self, filename: str) -> None:
        """Load a specific config file and merge with existing config"""
        file_path = self.config_dir / filename
        if file_path.exists():
            try:
                with open(file_path) as f:
                    config_data = json.load(f)
                    self.merge_config(config_data)
            except json.JSONDecodeError as e:
                print(f"Error reading config file {filename}: {e}")
    
    def merge_config(self, new_config: Dict) -> None:
        """Merge new config data with existing config"""
        for section, values in new_config.items():
            if section not in self.config:
                self.config[section] = {}
            if isinstance(values, dict):
                self.config[section].update(values)
    
    def save_default_configs(self) -> None:
        """Save default configurations to separate files"""
        game_config = {
            "game": self.DEFAULT_CONFIG["game"]
        }
        network_config = {
            "server": self.DEFAULT_CONFIG["server"]
        }
        
        self.save_config_file("game_settings.json", game_config)
        self.save_config_file("network.json", network_config)
    
    def save_config_file(self, filename: str, config_data: Dict) -> None:
        """Save config data to a specific file"""
        file_path = self.config_dir / filename
        try:
            with open(file_path, 'w') as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"Error saving config file {filename}: {e}")
    
    def get(self, section: str, key: str) -> Any:
        """Get a config value"""
        return self.config.get(section, {}).get(key)
    
    def set(self, section: str, key: str, value: Any) -> None:
        """Set a config value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
