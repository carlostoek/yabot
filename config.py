import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# config.py
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")  # Loaded from .env file