from db.connection import get_nodes_collection, get_edges_collection


# ─── Single node fetch ─────────────────────────────────────────

def get_node(node_id: str) -> dict | None:
    """
    Fetch a single node by its _id.
    Returns None if not found.
    """
    nodes = get_nodes_collection()
    return nodes.find_one({"_id": node_id})


# ─── Task memory fetch ─────────────────────────────────────────

def get_task_memory(task_id: str) -> dict:
    """
    Fetch a task node plus all nodes directly connected to it (1 hop).
    Returns a structured dict with the task and its related nodes grouped by type.
    """
    nodes = get_nodes_collection()
    edges = get_edges_collection()

    # Get the task itself
    task = nodes.find_one({"_id": task_id})
    if not task:
        return {}

    # Get all edges where this task is the source
    task_edges = list(edges.find({"from_id": task_id}))

    # For each edge, fetch the target node
    memory = {
        "task": task,
        "tools": [],
        "facts": [],
        "decisions": [],
        "related_tasks": []
    }

    for edge in task_edges:
        target = nodes.find_one({"_id": edge["to_id"]})
        if not target:
            continue

        relation = edge["relation"]

        if relation == "USED_TOOL":
            memory["tools"].append(target)
        elif relation == "LEARNED":
            memory["facts"].append(target)
        elif relation == "MADE_DECISION":
            memory["decisions"].append(target)
        elif relation == "RELATED_TO":
            memory["related_tasks"].append(target)

    return memory


# ─── Keyword search across facts ──────────────────────────────

def search_facts(keyword: str) -> list[dict]:
    """
    Search for Fact nodes whose label or content contains the keyword.
    Uses MongoDB text-style regex search.
    Case-insensitive.
    """
    nodes = get_nodes_collection()

    results = list(nodes.find({
        "type": "Fact",
        "$or": [
            {"label": {"$regex": keyword, "$options": "i"}},
            {"properties.content": {"$regex": keyword, "$options": "i"}}
        ]
    }))

    print(f"[reader] Found {len(results)} facts matching '{keyword}'")
    return results


# ─── Related task search ───────────────────────────────────────

def get_related_tasks(task_id: str, max_depth: int = 2) -> list[dict]:
    """
    Uses $graphLookup to find tasks related to a given task,
    following RELATED_TO edges recursively up to max_depth hops.

    This is the graph traversal — not possible in a regular database.
    """
    edges = get_edges_collection()
    nodes = get_nodes_collection()

    pipeline = [
        # Start with edges going out from this task
        {"$match": {
            "from_id": task_id,
            "relation": "RELATED_TO"
        }},

        # Recursively follow RELATED_TO edges
        {"$graphLookup": {
            "from": "edges",
            "startWith": "$to_id",
            "connectFromField": "to_id",
            "connectToField": "from_id",
            "restrictSearchWithMatch": {"relation": "RELATED_TO"},
            "as": "related_chain",
            "maxDepth": max_depth,
            "depthField": "hop_depth"
        }},

        # Pull all related task IDs into one flat array
        {"$project": {
            "all_related_ids": {
                "$concatArrays": [
                    ["$to_id"],
                    "$related_chain.to_id"
                ]
            }
        }}
    ]

    result = list(edges.aggregate(pipeline))

    if not result:
        return []

    # Flatten and deduplicate IDs
    all_ids = list(set(result[0]["all_related_ids"]))

    # Fetch the actual node documents
    related_nodes = list(nodes.find({
        "_id": {"$in": all_ids},
        "type": "Task"
    }))

    print(f"[reader] Found {len(related_nodes)} related tasks for task {task_id}")
    return related_nodes


# ─── Full context builder ──────────────────────────────────────

def get_full_context(keyword: str) -> dict:
    """
    The agent calls this before starting any new task.

    Given a keyword from the new task description:
    1. Finds all facts matching the keyword
    2. Finds tasks that produced those facts
    3. Pulls full memory (tools, decisions) for those tasks
    4. Returns everything as structured context

    This is what gives the agent its memory.
    """
    print(f"\n[reader] Building full context for keyword: '{keyword}'")
    nodes = get_nodes_collection()
    edges = get_edges_collection()

    # Step 1 — find relevant facts
    relevant_facts = search_facts(keyword)
    if not relevant_facts:
        print(f"[reader] No existing memory found for '{keyword}'")
        return {"facts": [], "tasks": [], "decisions": [], "tools": []}

    fact_ids = [f["_id"] for f in relevant_facts]

    # Step 2 — find tasks that produced those facts (reverse edge lookup)
    source_edges = list(edges.find({
        "to_id": {"$in": fact_ids},
        "relation": "LEARNED"
    }))
    source_task_ids = list(set(e["from_id"] for e in source_edges))

    # Step 3 — for each source task, get its full memory
    all_facts = []
    all_decisions = []
    all_tools = []
    all_tasks = []

    for task_id in source_task_ids:
        memory = get_task_memory(task_id)
        if memory:
            all_tasks.append(memory["task"])
            all_facts.extend(memory["facts"])
            all_decisions.extend(memory["decisions"])
            all_tools.extend(memory["tools"])

    # Deduplicate by _id
    def dedupe(items):
        seen = set()
        result = []
        for item in items:
            if item["_id"] not in seen:
                seen.add(item["_id"])
                result.append(item)
        return result

    context = {
        "tasks": dedupe(all_tasks),
        "facts": dedupe(all_facts),
        "decisions": dedupe(all_decisions),
        "tools": dedupe(all_tools)
    }

    print(f"[reader] Context built — "
          f"{len(context['tasks'])} tasks, "
          f"{len(context['facts'])} facts, "
          f"{len(context['decisions'])} decisions, "
          f"{len(context['tools'])} tools")

    return context