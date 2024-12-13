import discord
from discord.ext import commands
import heapq
from src.utils.indexer import MessageIndexer
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class KeywordCounter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.indexer = MessageIndexer()
        self.processing = False

    async def update_index(self, channel, progress_message):
        """
        Update channel index with progress tracking
        
        Args:
            channel: Discord channel to index
            progress_message: Message object to update progress
        """
        try:
            async def progress_callback(count):
                await progress_message.edit(
                    content=f"正在索引 {channel.name}: 已處理 {count} 條訊息"
                )

            total = await self.indexer.index_channel(channel, progress_callback)
            return total
        except Exception as e:
            logger.error(f"Error indexing channel {channel.name}: {e}")
            return 0

    @commands.command(name='更新索引')
    async def update_indices(self, ctx, channel_type: str = "current"):
        """
        Update index for specified range of channels
        
        Args:
            ctx: Command context
            channel_type: Type of channels to process (current/all/category)
        """
        if self.processing:
            await ctx.send("已有索引任務在執行中")
            return

        try:
            self.processing = True
            channels = self._get_channels(ctx, channel_type)
            if not channels:
                await ctx.send("找不到要處理的頻道")
                return

            # Initial status message
            status_message = await ctx.send(
                f"正在準備索引 {len(channels)} 個頻道...\n"
                "請稍候..."
            )

            processed_channels = {}
            
            async def progress_callback(channel, count):
                # Track progress for each channel
                processed_channels[channel.id] = count
                active_count = len(processed_channels)
                total_count = sum(processed_channels.values())
                
                progress_text = (
                    f"正在索引中... ({active_count}/{len(channels)} 頻道)\n"
                    f"已處理訊息數: {total_count:,}\n\n"
                    f"最近處理的頻道:\n"
                )
                
                # Show status of 5 most recent channels
                recent = list(processed_channels.items())[-5:]
                for ch_id, msg_count in recent:
                    channel = ctx.guild.get_channel(ch_id)
                    if channel:
                        progress_text += f"- {channel.name}: {msg_count:,} 訊息\n"
                
                try:
                    await status_message.edit(content=progress_text)
                except discord.errors.HTTPException:
                    # Fallback to shorter message if too long
                    await status_message.edit(
                        content=f"處理中... {active_count}/{len(channels)} 頻道, "
                        f"{total_count:,} 訊息"
                    )

            try:
                total_indexed = await self.indexer.index_channels(channels, progress_callback)
                summary = (
                    f"索引完成！\n"
                    f"處理頻道數: {len(channels)}\n"
                    f"索引訊息數: {total_indexed:,}"
                )
                await status_message.edit(content=summary)
            except Exception as e:
                await status_message.edit(
                    content=f"索引過程中發生錯誤: {str(e)}\n"
                    f"請查看日誌以獲取詳細資訊"
                )
                raise

        except Exception as e:
            logger.error(f"Error updating index: {e}", exc_info=True)
            await ctx.send(f"發生錯誤: {str(e)}")
        finally:
            self.processing = False

    @commands.command(name='統計關鍵字')
    async def analyze_keywords(self, ctx, channel_type: str = "current", *keywords):
        """
        Analyze keyword usage in messages
        
        Args:
            ctx: Command context
            channel_type: Type of channels to analyze
            keywords: Keywords to search for
        """
        if not keywords:
            await ctx.send("請提供要分析的關鍵字！")
            return

        if self.processing:
            await ctx.send("另一個分析任務正在進行中")
            return

        try:
            self.processing = True
            channels = self._get_channels(ctx, channel_type)
            channel_ids = [str(c.id) for c in channels]

            # Search using index
            progress_message = await ctx.send("搜尋訊息中...")
            results = self.indexer.search_messages(keywords, channel_ids)

            # Display results
            for keyword, user_counts in results.items():
                if user_counts:
                    top_users = heapq.nlargest(3, user_counts.items(), key=lambda x: x[1])
                    result_msg = f"\n關鍵字 '{keyword}' 的結果：\n"
                    for user, count in top_users:
                        result_msg += f"- {user}: {count} 次\n"
                    result_msg += f"\n總計出現：{sum(user_counts.values())} 次"
                    await ctx.send(result_msg)
                else:
                    await ctx.send(f"找不到關鍵字 '{keyword}' 的使用記錄")

        except Exception as e:
            logger.error(f"Error in keyword analysis: {e}")
            await ctx.send(f"發生錯誤：{str(e)}")
        finally:
            self.processing = False

    def _get_channels(self, ctx, channel_type: str):
        """
        Helper method to get channels based on type
        
        Args:
            ctx: Command context
            channel_type: Type of channels to retrieve (current/all/category)
            
        Returns:
            List of Discord text channels
        """
        if channel_type == "current":
            return [ctx.channel]
        elif channel_type == "all":
            return [c for c in ctx.guild.channels if isinstance(c, discord.TextChannel)]
        elif channel_type == "category":
            if ctx.channel.category:
                return [c for c in ctx.channel.category.channels if isinstance(c, discord.TextChannel)]
        return []

async def setup(bot):
    """Initialize the cog with the bot"""
    await bot.add_cog(KeywordCounter(bot))