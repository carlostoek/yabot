"""
Handlers module for the bot framework
"""
from aiogram import Router
from . import commands
from . import default
from . import base
from . import webhook

# Create main router for the bot
main_router = Router()

__all__ = [
    'commands',
    'default',
    'base',
    'webhook',
    'main_router'
]