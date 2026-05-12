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

if __name__ == "__main__":
    test_reader()