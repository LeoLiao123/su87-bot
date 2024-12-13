import asyncio
from datetime import datetime
from typing import List, Dict, Set
from sqlalchemy import or_
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from src.database import Message, init_db
import concurrent.futures
import time
import discord
from contextlib import contextmanager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class MessageIndexer:
    def __init__(self):
        # Get sessionmaker instance
        self.Session = sessionmaker(bind=init_db())
        self.last_indexed = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.batch_size = 1000
        self.processing_semaphore = asyncio.Semaphore(5)

    @contextmanager
    def get_session(self):
        """Create a new database session with context management"""
        session = self.Session()  # Create new session
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    async def _process_message_batch(self, messages: List[discord.Message]) -> List[dict]:
        """Process a batch of messages and convert to dictionary format"""
        return [{
            'discord_message_id': str(message.id),
            'channel_id': str(message.channel.id),
            'author_id': str(message.author.id),
            'author_name': message.author.name,
            'content': message.content,
            'created_at': message.created_at
        } for message in messages]

    async def _save_messages(self, message_dicts: List[dict]):
        """Save messages to database"""
        async with self.processing_semaphore:
            def db_operation():
                with self.get_session() as session:
                    messages = [Message(**data) for data in message_dicts]
                    session.bulk_save_objects(messages)
                    # Session will commit automatically via context manager

            try:
                await asyncio.get_event_loop().run_in_executor(
                    self.executor, 
                    db_operation
                )
            except Exception as e:
                print(f"Error saving messages: {e}")
                raise

    async def index_channel(self, channel, progress_callback=None):
        """Index channel using stream processing and memory management
        
        Args:
            channel: Discord channel to index
            progress_callback: Callback function for progress updates
            
        Returns:
            int: Total number of messages indexed
        """
        total_indexed = 0
        current_batch = []
        last_progress_update = time.time()
        
        try:
            # Get list of existing message IDs
            with self.get_session() as session:
                existing_ids = set(
                    row[0] for row in session.query(Message.discord_message_id)
                    .filter_by(channel_id=str(channel.id))
                    .all()
                )

            # Process messages in streaming fashion
            async for message in channel.history(limit=None):
                if str(message.id) in existing_ids:
                    continue

                # Store only necessary message data
                message_data = {
                    'discord_message_id': str(message.id),
                    'channel_id': str(channel.id),
                    'author_id': str(message.author.id),
                    'author_name': message.author.name,
                    'content': message.content,
                    'created_at': message.created_at
                }
                
                current_batch.append(message_data)
                total_indexed += 1

                # Process batch when size limit is reached
                if len(current_batch) >= self.batch_size:
                    await self._save_batch(current_batch)
                    current_batch = []
                    
                    # Force garbage collection
                    import gc
                    gc.collect()

                    # Update progress
                    current_time = time.time()
                    if current_time - last_progress_update >= 2.0:
                        if progress_callback:
                            await progress_callback(total_indexed)
                        last_progress_update = current_time

            # Process remaining messages
            if current_batch:
                await self._save_batch(current_batch)

        except Exception as e:
            logger.error(f"Error indexing channel {channel.name}: {e}")
            raise

        return total_indexed

    async def _save_batch(self, batch):
        """Save a batch of messages to database"""
        async with self.processing_semaphore:
            def db_operation():
                with self.get_session() as session:
                    messages = [Message(**data) for data in batch]
                    session.bulk_save_objects(messages)

            try:
                await asyncio.get_event_loop().run_in_executor(
                    self.executor, 
                    db_operation
                )
            except Exception as e:
                logger.error(f"Error saving batch: {e}")
                raise

    def search_messages(self, keywords: List[str], channel_ids: List[str] = None) -> Dict[str, Dict[str, int]]:
        """Search for messages containing keywords
        
        Args:
            keywords: List of keywords to search for
            channel_ids: Optional list of channel IDs to limit search
            
        Returns:
            Dict mapping keywords to user message counts
        """
        results = {}
        
        with self.get_session() as session:
            for keyword in keywords:
                query = session.query(Message)
                
                keyword_filter = Message.content.ilike(f'%{keyword}%')
                if channel_ids:
                    query = query.filter(Message.channel_id.in_(channel_ids))
                
                messages = query.filter(keyword_filter).all()
                
                user_counts = {}
                for msg in messages:
                    user_counts[msg.author_name] = user_counts.get(msg.author_name, 0) + 1
                
                results[keyword] = user_counts
                
        return results
    
    async def index_channels(self, channels: List[discord.TextChannel], progress_callback=None):
        """Process multiple channels concurrently using queue system
        
        Args:
            channels: List of Discord channels to process
            progress_callback: Callback function for progress updates
            
        Returns:
            int: Total number of messages processed
        """
        total_messages = 0
        active_tasks = []
        max_concurrent = 3
        queue = asyncio.Queue()
        processed_channels = 0

        async def worker():
            """Worker coroutine to process channels from queue"""
            nonlocal total_messages, processed_channels
            while True:
                try:
                    channel = await queue.get()
                    if channel is None:
                        queue.task_done()
                        logger.debug("Worker 收到結束信號")
                        break

                    logger.info(f"開始處理頻道: {channel.name}")
                    try:
                        messages_processed = await self.index_channel(
                            channel,
                            lambda count, ch=channel: progress_callback(ch, count) 
                            if progress_callback else None
                        )
                        total_messages += messages_processed
                        processed_channels += 1
                        logger.info(
                            f"完成索引頻道 {channel.name}: {messages_processed} 則訊息 "
                            f"({processed_channels}/{len(channels)} 頻道完成)"
                        )
                    except discord.Forbidden:
                        logger.warning(f"無權限存取頻道 {channel.name}")
                    except Exception as e:
                        logger.error(f"處理頻道 {channel.name} 時發生錯誤: {e}", exc_info=True)
                    finally:
                        queue.task_done()
                        import gc
                        gc.collect()

                except Exception as e:
                    logger.error(f"Worker 發生錯誤: {e}", exc_info=True)

        logger.info(f"開始處理 {len(channels)} 個頻道，同時處理數: {max_concurrent}")

        # Create workers
        for i in range(max_concurrent):
            task = asyncio.create_task(worker())
            active_tasks.append(task)
            logger.debug(f"創建 Worker {i+1}")

        # Add channels to queue
        for channel in channels:
            await queue.put(channel)
            logger.debug(f"將頻道 {channel.name} 加入佇列")

        # Add end signals
        for _ in range(max_concurrent):
            await queue.put(None)

        try:
            # Wait for queue to complete
            await asyncio.wait_for(queue.join(), timeout=60000)  # 1000 minutes timeout
            logger.info("佇列處理完成")
        except asyncio.TimeoutError:
            logger.error("處理超時")
            raise

        # Wait for all workers to finish
        await asyncio.gather(*active_tasks, return_exceptions=True)
        logger.info(f"索引完成，共處理 {total_messages} 則訊息")

        return total_messages