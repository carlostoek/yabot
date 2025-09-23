import json
import os
from typing import Dict, Any, Optional

# Define the path to the database file
DB_FILE = os.path.join(os.path.dirname(__file__), 'db.json')

def get_user_profile(telegram_id: str) -> Dict[str, Any]:
    """
    Retrieves a user profile from the database. If the user doesn't exist,
    creates a new profile with default values.
    
    Args:
        telegram_id (str): The Telegram ID of the user
        
    Returns:
        dict: The user profile
    """
    # Load existing data
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        data = {}
    
    # Check if user exists
    if telegram_id in data:
        return data[telegram_id]
    
    # Create new user profile with default values
    user_profile = {
        "telegram_id": telegram_id,
        "username": None,
        "first_name": "Usuario",
        "kisses": 5,
        "inventory": [],
        "achievements": [],
        "role": "free",
        "vip_expiry": None,
        "last_daily_claim": None,
        "current_narrative_fragment": None,
        "narrative_choices": {},
        "metadata": {}
    }
    
    # Save the new profile
    data[telegram_id] = user_profile
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return user_profile

def save_user_profile(user_profile: Dict[str, Any]) -> None:
    """
    Saves a user profile to the database, overwriting the existing one.
    
    Args:
        user_profile (dict): The complete user profile to save
    """
    # Load existing data
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        data = {}
    
    # Update the user profile
    telegram_id = user_profile["telegram_id"]
    data[telegram_id] = user_profile
    
    # Save the updated data
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)