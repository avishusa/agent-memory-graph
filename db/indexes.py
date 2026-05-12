from pymongo import ASCENDING, TEXT
from connection import get_nodes_collection, get_edges_collection


def create_indexes():
    """
    Creates all indexes for the knowledge graph collections.

    This is idempotent — safe to run multiple times.
    MongoDB skips creating an index if it already exists with the same spec.

    Always run this once on fresh environments (new machine, new Atlas cluster).
    """
    nodes = get_nodes_collection()
    edges = get_edges_collection()

    print("[indexes] Creating indexes...")

    # ── Nodes collection ───────────────────────────────────────

    # Query pattern: find all nodes of a specific type
    # e.g. nodes.find({"type": "Task"})
    nodes.create_index(
        [("type", ASCENDING)],
        name="idx_nodes_type"
    )

    # Query pattern: find a node by type AND label
    # e.g. nodes.find({"type": "Tool", "label": "read_file"})
    # Compound index — type first because it has higher cardinality filter
    nodes.create_index(
        [("type", ASCENDING), ("label", ASCENDING)],
        name="idx_nodes_type_label"
    )

    # Query pattern: full text search on facts
    # e.g. search_facts("JWT") — searches label and properties.content
    # TEXT index lets MongoDB do keyword search across multiple fields
    nodes.create_index(
        [("label", TEXT), ("properties.content", TEXT)],
        name="idx_nodes_text_search"
    )

    # ── Edges collection ───────────────────────────────────────

    # Query pattern: find all edges going OUT from a node
    # e.g. edges.find({"from_id": task_id})
    # Also used by $graphLookup as the connectToField
    edges.create_index(
        [("from_id", ASCENDING)],
        name="idx_edges_from_id"
    )

    # Query pattern: find all edges coming IN to a node
    # e.g. edges.find({"to_id": fact_id})
    # Also used by $graphLookup as the startWith field
    edges.create_index(
        [("to_id", ASCENDING)],
        name="idx_edges_to_id"
    )

    # Query pattern: find edges by source AND relation type
    # e.g. edges.find({"from_id": task_id, "relation": "LEARNED"})
    # Compound — from_id first (equality), relation second (equality)
    edges.create_index(
        [("from_id", ASCENDING), ("relation", ASCENDING)],
        name="idx_edges_from_relation"
    )

    # Query pattern: find edges by destination AND relation type
    # e.g. edges.find({"to_id": fact_id, "relation": "LEARNED"})
    # Used in get_full_context() reverse lookup
    edges.create_index(
        [("to_id", ASCENDING), ("relation", ASCENDING)],
        name="idx_edges_to_relation"
    )

    print("[indexes] Done. Indexes created:")
    print(f"  nodes: {[i['name'] for i in nodes.list_indexes()]}")
    print(f"  edges: {[i['name'] for i in edges.list_indexes()]}")


if __name__ == "__main__":
    create_indexes()