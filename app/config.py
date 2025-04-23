import configparser
import os

def load_config(config_file_path):
    """
    Loads configuration from .config file
    """
    config = configparser.ConfigParser()
    config.read("/app/app/config.ini")
    return config

script_dir = os.path.dirname(os.path.abspath(__file__))
config_file_path = os.path.join(script_dir, 'config.ini')

if not os.path.exists(config_file_path):
    raise FileNotFoundError(f"Configuration file not found: {config_file_path}")

config = load_config(config_file_path)
config["AUTH0"]