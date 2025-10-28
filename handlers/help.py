from telegram import Update
from telegram.ext import ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /help command.
    
    Args:
        update (Update): The update object from Telegram
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram
    """
    help_message = (
        "¡Hola! Soy DianaBot, tu guía en esta aventura. Aquí están los comandos disponibles:\n\n"
        "/start - Inicia la aventura conmigo\n"
        "/help - Muestra este mensaje de ayuda\n\n"
        "¡Explora y diviértete!"
    )
    await update.message.reply_text(help_message)