from typing import Dict, Tuple, List
import discord
import asyncio
from collections import defaultdict
from ...config import settings

async def process_messages(
    channel,
    keyword: str,
    progress_message: discord.Message,
    batch_size: int = settings.BATCH_SIZE,
    sleep_time: float = settings.SLEEP_TIME
) -> Tuple[Dict[str, int], int]:
    """
    Process messages to count keyword usage
    
    Args:
        channel: Discord channel to process
        keyword: Keyword to search for
        progress_message: Message to update with progress
        batch_size: Number of messages to process in each batch
        sleep_time: Time to sleep between batches
        
    Returns:
        Tuple containing user counts and total messages processed
    """
    user_counts = defaultdict(int)
    total_messages = 0
    last_message = None

    while True:
        try:
            messages = []
            if last_message is None:
                async for msg in channel.history(limit=batch_size):
                    if isinstance(msg, discord.Message):
                        messages.append(msg)
            else:
                async for msg in channel.history(limit=batch_size, before=last_message):
                    if isinstance(msg, discord.Message):
                        messages.append(msg)

            if not messages:
                break

            valid_messages = []
            for message in messages:
                try:
                    if not isinstance(message, discord.Message):
                        continue
                    if not hasattr(message, 'content') or not hasattr(message, 'author'):
                        continue
                    valid_messages.append(message)
                    if keyword in message.content:
                        user_counts[message.author.name] += 1
                except AttributeError:
                    continue

            if not valid_messages:
                break

            total_messages += len(valid_messages)
            try:
                await progress_message.edit(
                    content=f"Analyzing keyword '{keyword}'...\n"
                           f"Processed {total_messages} messages"
                )
            except discord.errors.NotFound:
                break

            last_message = valid_messages[-1]
            await asyncio.sleep(sleep_time)

        except discord.errors.HTTPException as e:
            print(f"Hit Discord API rate limit, waiting to continue: {e}")
            await asyncio.sleep(5)
            continue
        except Exception as e:
            print(f"Error while searching for keyword {keyword}: {e}")
            break

    return user_counts, total_messages