from telegram import Update
from telegram.ext import ContextTypes
from database.user_db import get_user_profile

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    
    Args:
        update (Update): The update object from Telegram
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram
    """
    # Extract user information
    user = update.effective_user
    telegram_id = str(user.id)
    username = user.username
    first_name = user.first_name if user.first_name else "Usuario"
    
    # Get or create user profile
    user_profile = get_user_profile(telegram_id)
    
    # Update user profile with current information
    user_profile["username"] = username
    user_profile["first_name"] = first_name
    
    # Send welcome message
    welcome_message = f"¡Hola {first_name}! 👋 Soy DianaBot, tu guía en esta aventura. Usa /ayuda para ver los comandos disponibles."
    await update.message.reply_text(welcome_message)