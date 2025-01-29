import json
import re
from sqlalchemy.orm import sessionmaker
from src.database import Message, init_db

# Initialize the database session
engine = init_db()
Session = sessionmaker(bind=engine)
session = Session()

def get_user_message_history(author_id: str):
    try:
        messages = session.query(Message).filter_by(author_name=author_id).order_by(Message.created_at.desc()).all()
        return messages
    except Exception as e:
        print(f"Error retrieving message history: {e}")
        return []
    finally:
        session.close()

def contains_chinese(text):
    """Check if the text contains any Chinese characters"""
    return re.search(r'[\u4e00-\u9fff]', text) is not None

def is_valid_message(content):
    """Check if the message content is valid (not empty, not a GIF, not an image)"""
    if not content.strip():
        return False
    if re.search(r'\bhttps?://\S+\.(?:jpg|jpeg|png|gif)\b', content):
        return False
    return True

def format_messages_for_training(messages):
    training_data = []
    for message in messages:
        if is_valid_message(message.content):
            training_data.append({
                "prompt": f"{message.author_name}: ",
                "completion": f"{message.content}\n"
            })
    return training_data

def save_to_jsonl(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for entry in data:
            json.dump(entry, f, ensure_ascii=False)
            f.write('\n')

# Example usage
user_id = 'super_sus514'
message_history = get_user_message_history(user_id)
training_data = format_messages_for_training(message_history)
save_to_jsonl(training_data, 'user_chat_history.jsonl')

print(f"Saved {len(training_data)} messages to user_chat_history.jsonl")
