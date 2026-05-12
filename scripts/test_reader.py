import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_nodes_collection
from graph.reader import (
    search_facts,
    get_task_memory,
    get_full_context
)

def test_reader():

    # ── Test 1: search facts by keyword ───────────────────────
    print("=" * 50)
    print("TEST 1 — search_facts('JWT')")
    print("=" * 50)
    facts = search_facts("JWT")
    for f in facts:
        print(f"  └─ {f['label']}")
        print(f"       {f['properties']['content']}")

    # ── Test 2: get full memory of the first task ──────────────
    print("\n" + "=" * 50)
    print("TEST 2 — get_task_memory() for first task")
    print("=" * 50)
    nodes = get_nodes_collection()
    first_task = nodes.find_one({"type": "Task"})
    if first_task:
        memory = get_task_memory(first_task["_id"])
        print(f"Task: {memory['task']['label']}")
        print(f"  Tools used:     {[t['label'] for t in memory['tools']]}")
        print(f"  Facts learned:  {[f['label'] for f in memory['facts']]}")
        print(f"  Decisions made: {[d['label'] for d in memory['decisions']]}")

    # ── Test 3: get full context for a new task ────────────────
    print("\n" + "=" * 50)
    print("TEST 3 — get_full_context('auth')")
    print("=" * 50)
    context = get_full_context("auth")
    print(f"\nContext returned:")
    print(f"  Past tasks:  {[t['label'] for t in context['tasks']]}")
    print(f"  Known facts: {[f['label'] for f in context['facts']]}")
    print(f"  Decisions:   {[d['label'] for d in context['decisions']]}")
    print(f"  Tools seen:  {[t['label'] for t in context['tools']]}")

    print("\n[ok] Reader tests complete.")

def test_indexes():
    """
    Uses explain() to verify MongoDB is using indexes, not doing collection scans.
    COLLSCAN = bad (no index). IXSCAN = good (index used).
    """
    from db.connection import get_nodes_collection, get_edges_collection

    print("\n" + "=" * 50)
    print("TEST — Index usage verification")
    print("=" * 50)

    nodes = get_nodes_collection()
    edges = get_edges_collection()

    # Check nodes type query
    plan = nodes.find({"type": "Task"}).explain()
    stage = plan["queryPlanner"]["winningPlan"].get("stage", "")
    input_stage = plan["queryPlanner"]["winningPlan"].get("inputStage", {}).get("stage", "")
    actual_stage = input_stage or stage
    status = "✅ IXSCAN" if "IXSCAN" in actual_stage else "❌ COLLSCAN"
    print(f"nodes.find(type=Task)        → {status}")

    # Check edges from_id query
    plan = edges.find({"from_id": "any-id"}).explain()
    stage = plan["queryPlanner"]["winningPlan"].get("stage", "")
    input_stage = plan["queryPlanner"]["winningPlan"].get("inputStage", {}).get("stage", "")
    actual_stage = input_stage or stage
    status = "✅ IXSCAN" if "IXSCAN" in actual_stage else "❌ COLLSCAN"
    print(f"edges.find(from_id=...)      → {status}")

    # Check edges compound query
    plan = edges.find({"from_id": "any-id", "relation": "LEARNED"}).explain()
    stage = plan["queryPlanner"]["winningPlan"].get("stage", "")
    input_stage = plan["queryPlanner"]["winningPlan"].get("inputStage", {}).get("stage", "")
    actual_stage = input_stage or stage
    status = "✅ IXSCAN" if "IXSCAN" in actual_stage else "❌ COLLSCAN"
    print(f"edges.find(from+relation)    → {status}")

# add this to the bottom of the file
if __name__ == "__main__":
    test_reader()
    test_indexes()

if __name__ == "__main__":
    test_reader()