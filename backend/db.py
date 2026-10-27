"""MongoDB connection and collection setup."""
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from urllib.parse import quote, unquote

load_dotenv()

_client = None

def _normalise_connection_string(value):
    """Escape raw Atlas credentials while preserving an already encoded URI."""
    scheme, separator, remainder = value.partition('://')
    if not separator or '@' not in remainder:
        return value
    userinfo, at, server_and_options = remainder.rpartition('@')
    if ':' not in userinfo:
        return value
    username, password = userinfo.split(':', 1)
    return (
        f'{scheme}://{quote(unquote(username), safe="")}:'
        f'{quote(unquote(password), safe="")}@{server_and_options}'
    )

def get_database():
    global _client
    mongodb_url = os.getenv('MONGODB_URL')
    if not mongodb_url:
        raise RuntimeError('MONGODB_URL is not configured. Add it to the project .env file.')
    if _client is None:
        _client = MongoClient(_normalise_connection_string(mongodb_url), serverSelectionTimeoutMS=5000)
    client = _client
    db = client[os.getenv('DATABASE_NAME', 'textile_sentiment')]
    db.users.create_index('email', unique=True)
    db.products.create_index('category')
    db.products.create_index('seasonal_tags')
    db.reviews.create_index('product_id')
    db.reviews.create_index('season')
    db.reviews.create_index('timestamp')
    db.seasonal_metadata.create_index('season', unique=True)
    return db

