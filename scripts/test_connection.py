import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_db, get_nodes_collection, get_edges_collection

def test_connection():
    print("Testing MongoDB connection...")

    db = get_db()
    print(f"[ok] Database reached: {db.name}")

    nodes = get_nodes_collection()
    edges = get_edges_collection()
    print(f"[ok] Collections ready: '{nodes.name}', '{edges.name}'")

    print("\nAll checks passed. You are ready for Step 3.")

if __name__ == "__main__":
    test_connection()