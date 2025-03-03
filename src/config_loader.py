import os
import yaml
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Configuration loader utility for the application"""
    
    def __init__(self, config_dir: str = 'config'):
        """Initialize the configuration loader
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir
        self.settings = {}
        self.markets = {}
        self.sources = {}
        
        # Create config directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(os.path.join(config_dir, 'sources'), exist_ok=True)
        
        # Load configurations
        self._load_settings()
        self._load_markets()
        self._load_sources()
        
        logger.info(f"Configuration loaded: {len(self.markets)} markets, {len(self.sources)} sources")
    
    def _load_yaml(self, filepath: str) -> Dict:
        """Load a YAML file
        
        Args:
            filepath: Path to the YAML file
            
        Returns:
            Dictionary containing the YAML contents
        """
        try:
            if not os.path.exists(filepath):
                logger.warning(f"Configuration file not found: {filepath}")
                return {}
                
            with open(filepath, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Error loading configuration from {filepath}: {str(e)}")
            return {}
    
    def _load_settings(self) -> None:
        """Load global settings"""
        settings_path = os.path.join(self.config_dir, 'settings.yaml')
        self.settings = self._load_yaml(settings_path)
    
    def _load_markets(self) -> None:
        """Load market configurations"""
        markets_path = os.path.join(self.config_dir, 'markets.yaml')
        self.markets = self._load_yaml(markets_path)
    
    def _load_sources(self) -> None:
        """Load source configurations"""
        sources_dir = os.path.join(self.config_dir, 'sources')
        
        for filename in os.listdir(sources_dir):
            if filename.endswith('.yaml'):
                source_name = filename.replace('.yaml', '')
                filepath = os.path.join(sources_dir, filename)
                self.sources[source_name] = self._load_yaml(filepath)
    
    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """Get a setting value
        
        Args:
            section: Setting section
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        if section in self.settings and key in self.settings[section]:
            return self.settings[section][key]
        return default
    
    def get_market(self, market_id: str) -> Optional[Dict]:
        """Get market configuration
        
        Args:
            market_id: Market identifier
            
        Returns:
            Market configuration dictionary or None if not found
        """
        return self.markets.get(market_id)
    
    def get_markets(self) -> Dict:
        """Get all market configurations
        
        Returns:
            Dictionary of all market configurations
        """
        return self.markets
    
    def get_enabled_markets(self) -> Dict:
        """Get enabled market configurations
        
        Returns:
            Dictionary of enabled market configurations
        """
        return {k: v for k, v in self.markets.items() if not v.get('disabled', False)}
    
    def get_source_config(self, source_name: str) -> Optional[Dict]:
        """Get source configuration
        
        Args:
            source_name: Source name (youtube, twitter, radio)
            
        Returns:
            Source configuration dictionary or None if not found
        """
        return self.sources.get(source_name)
    
    def get_markets_for_source(self, source_name: str, channel_name: Optional[str] = None) -> List[Dict]:
        """Get markets configured for a specific source
        
        Args:
            source_name: Source name
            channel_name: Optional channel name for filtering
            
        Returns:
            List of market configurations for the source
        """
        source_config = self.get_source_config(source_name)
        if not source_config:
            return []
        
        # If channel specified, filter to markets for that channel
        if channel_name and 'channels' in source_config:
            for channel in source_config['channels']:
                if channel['name'] == channel_name and channel.get('active', True):
                    market_ids = channel.get('markets', [])
                    return [self.get_market(market_id) for market_id in market_ids 
                            if self.get_market(market_id)]
        
        # Otherwise return all enabled markets
        return list(self.get_enabled_markets().values())

# Singleton instance
config = ConfigLoader()

def get_config() -> ConfigLoader:
    """Get the configuration loader instance
    
    Returns:
        ConfigLoader instance
    """
    return config