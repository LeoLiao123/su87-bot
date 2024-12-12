import discord
from discord.ext import commands
import asyncio
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.config import settings
from src.utils.logger import setup_logger

# Set up logging
logger = setup_logger(__name__)

# Configure intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix=settings.COMMAND_PREFIX, intents=intents)

@bot.event
async def on_ready():
    """Event handler for when the bot is ready"""
    logger.info(f'Bot has logged in as {bot.user.name}')

async def main():
    """Main async function to run the bot"""
    async with bot:
        # Load all cogs
        await bot.load_extension('src.cogs.keyword_counter.cog')
        logger.info("All cogs loaded successfully")
        
        # Start the bot
        await bot.start(settings.DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")