import discord
from discord.ext import commands
import asyncio
import os
import sys

# Add the src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Configure intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix=settings.COMMAND_PREFIX, intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Bot has logged in as {bot.user.name}')

async def main():
    async with bot:
        try:
            # Make sure this path matches your file structure
            await bot.load_extension('src.cogs.keyword_counter')
            logger.info("Keyword counter cog loaded")
            await bot.start(settings.DISCORD_TOKEN)
        except Exception as e:
            logger.error(f"Failed to start bot: {e}", exc_info=True)  # Added exc_info for more details

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)  # Added exc_info for more details