import discord
from discord.ext import commands
from collections import defaultdict
import heapq
from typing import List, Tuple
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.utils.logger import setup_logger
from .utils import process_messages

logger = setup_logger(__name__)

class KeywordCounter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.keyword_stats = defaultdict(lambda: defaultdict(int))

    async def get_top_users(self, stats: dict, n: int = 3) -> List[Tuple[str, int]]:
        """Get top N users by keyword usage count"""
        return heapq.nlargest(n, stats.items(), key=lambda x: x[1])

    @commands.command(name='統計關鍵字')
    async def analyze_keywords(self, ctx, *keywords):
        """
        Analyze keyword usage across all messages
        Usage: !統計關鍵字 [keyword1] [keyword2] ...
        """
        if not keywords:
            await ctx.send("Please provide keywords to analyze! Usage: !統計關鍵字 [keyword1] [keyword2] ...")
            return

        self.keyword_stats.clear()
        status_message = await ctx.send("Starting keyword analysis...")
        total_messages_all_keywords = 0

        for keyword in keywords:
            try:
                progress_message = await ctx.send(f"Starting analysis for keyword '{keyword}'...")
                user_counts, messages_processed = await process_messages(
                    ctx.channel,
                    keyword,
                    progress_message
                )
                
                total_messages_all_keywords = max(total_messages_all_keywords, messages_processed)
                self.keyword_stats[keyword] = user_counts

                top_users = await self.get_top_users(user_counts)
                result_message = f"\nResults for keyword '{keyword}':\n"
                
                if not top_users:
                    result_message += "- No usage found\n"
                else:
                    for user, count in top_users:
                        result_message += f"- {user}: {count} times\n"

                await ctx.send(result_message)
                try:
                    await progress_message.delete()
                except discord.errors.NotFound:
                    pass

            except Exception as e:
                error_msg = f"Error processing keyword '{keyword}': {str(e)}"
                logger.error(error_msg)
                await ctx.send(error_msg)

        try:
            summary = (
                f"Analysis complete!\n"
                f"- Total messages processed: {total_messages_all_keywords}\n"
                f"- Run command again if analysis was interrupted"
            )
            await status_message.edit(content=summary)
        except discord.errors.NotFound:
            await ctx.send(summary)

async def setup(bot):
    """Async setup function for the Cog"""
    await bot.add_cog(KeywordCounter(bot))