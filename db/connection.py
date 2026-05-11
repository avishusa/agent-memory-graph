import os
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

load_dotenv()

# ─── Module-level singleton ────────────────────────────────────
# These are created once when this module is first imported.
# Every other file that imports get_db() reuses the same connection.
_client: MongoClient = None
_db: Database = None


def get_db() -> Database:
    """
    Returns the MongoDB database instance.
    Creates the connection on first call, reuses it on every subsequent call.
    This is the singleton pattern for database connections.
    """
    global _client, _db

    if _db is not None:
        return _db

    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("DB_NAME", "agent_memory")

    if not uri:
        raise EnvironmentError(
            "MONGODB_URI not found. Did you create your .env file?"
        )

    try:
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Force a real connection attempt — MongoClient is lazy by default
        _client.admin.command("ping")
        _db = _client[db_name]
        print(f"[db] Connected to MongoDB — database: '{db_name}'")
        return _db

    except ConnectionFailure as e:
        raise ConnectionFailure(f"[db] Could not connect to MongoDB: {e}")


def get_nodes_collection():
    """Returns the nodes collection."""
    return get_db()["nodes"]


def get_edges_collection():
    """Returns the edges collection."""
    return get_db()["edges"]