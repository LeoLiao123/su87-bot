import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')

# Feature Configuration
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '1000'))
MAX_CONCURRENT_CHANNELS = int(os.getenv('MAX_CONCURRENT_CHANNELS', '3'))  
SLEEP_TIME = float(os.getenv('SLEEP_TIME', '1.0'))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')