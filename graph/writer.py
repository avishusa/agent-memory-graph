from datetime import datetime, timezone
from pymongo.collection import Collection
from db.connection import get_nodes_collection, get_edges_collection
from graph.schema import (
    make_node, make_edge,
    NODE_TASK, NODE_TOOL, NODE_FACT, NODE_DECISION, NODE_AGENT_ROLE,
    REL_USED_TOOL, REL_LEARNED, REL_MADE_DECISION,
    REL_RELATED_TO, REL_DEPENDS_ON,
    REL_PRODUCED_BY, REL_REVIEWS,
)


# ─── Individual node writers ───────────────────────────────────

def save_task(label: str, summary: str, status: str = "completed") -> str:
    """
    Creates a Task node in the graph.
    Returns the new node's _id.
    """
    nodes = get_nodes_collection()
    node = make_node(
        node_type=NODE_TASK,
        label=label,
        properties={"summary": summary, "status": status}
    )
    nodes.insert_one(node)
    print(f"[writer] Task saved: '{label}' ({node['_id']})")
    return node["_id"]


def save_tool(label: str, description: str = "") -> str:
    """
    Creates a Tool node if it doesn't already exist (upsert).
    Tools are reusable — 'read_file' should exist only once in the graph.
    Returns the tool node's _id.
    """
    nodes = get_nodes_collection()

    # Check if this tool already exists
    existing = nodes.find_one({"type": NODE_TOOL, "label": label})
    if existing:
        print(f"[writer] Tool already exists, reusing: '{label}' ({existing['_id']})")
        return existing["_id"]

    node = make_node(
        node_type=NODE_TOOL,
        label=label,
        properties={"description": description}
    )
    nodes.insert_one(node)
    print(f"[writer] Tool saved: '{label}' ({node['_id']})")
    return node["_id"]


def save_fact(label: str, content: str, confidence: float = 1.0) -> str:
    """
    Creates a Fact node in the graph.
    Facts are things the agent learned — they are always new entries.
    Returns the new node's _id.
    """
    nodes = get_nodes_collection()
    node = make_node(
        node_type=NODE_FACT,
        label=label,
        properties={"content": content, "confidence": confidence}
    )
    nodes.insert_one(node)
    print(f"[writer] Fact saved: '{label}' ({node['_id']})")
    return node["_id"]


def save_decision(label: str, reasoning: str) -> str:
    """
    Creates a Decision node in the graph.
    Decisions capture why the agent chose one approach over another.
    Returns the new node's _id.
    """
    nodes = get_nodes_collection()
    node = make_node(
        node_type=NODE_DECISION,
        label=label,
        properties={"reasoning": reasoning}
    )
    nodes.insert_one(node)
    print(f"[writer] Decision saved: '{label}' ({node['_id']})")
    return node["_id"]


def save_agent_role(label: str, description: str) -> str:
    """
    Creates an AgentRole node if one with this label doesn't exist (upsert).
    AgentRoles are singletons — there should be exactly one 'Researcher',
    one 'Critic', one 'Writer' for the entire lifetime of the system.
    All PRODUCED_BY edges from Facts/Decisions point to these singleton nodes.

    Returns the agent role node's _id (existing or newly created).
    """
    nodes = get_nodes_collection()

    # Check if this role already exists
    existing = nodes.find_one({"type": NODE_AGENT_ROLE, "label": label})
    if existing:
        print(f"[writer] AgentRole already exists, reusing: '{label}' ({existing['_id']})")
        return existing["_id"]

    node = make_node(
        node_type=NODE_AGENT_ROLE,
        label=label,
        properties={"description": description}
    )
    nodes.insert_one(node)
    print(f"[writer] AgentRole saved: '{label}' ({node['_id']})")
    return node["_id"]


# ─── Edge writer ───────────────────────────────────────────────

def link_nodes(
    from_id: str,
    from_type: str,
    relation: str,
    to_id: str,
    to_type: str,
    properties: dict = None
) -> str:
    """
    Creates an edge between two existing nodes.
    Validates types via make_edge() before inserting.
    Returns the new edge's _id.
    """
    edges = get_edges_collection()
    edge = make_edge(
        from_id=from_id,
        from_type=from_type,
        relation=relation,
        to_id=to_id,
        to_type=to_type,
        properties=properties or {}
    )
    edges.insert_one(edge)
    print(f"[writer] Edge saved: {from_type} --[{relation}]--> {to_type}")
    return edge["_id"]


# ─── High-level memory writer ──────────────────────────────────

def remember_task(
    task_label: str,
    task_summary: str,
    tools_used: list[str] = None,
    facts_learned: list[dict] = None,
    decisions_made: list[dict] = None,
    related_task_ids: list[str] = None,
) -> str:
    """
    The main function the agent calls after completing a task.
    Saves the task + all its relationships in one call.

    Args:
        task_label:      Short name for the task e.g. "Fix login bug"
        task_summary:    What the agent did and what happened
        tools_used:      List of tool names e.g. ["read_file", "edit_file"]
        facts_learned:   List of dicts: [{"label": ..., "content": ..., "confidence": ...}]
        decisions_made:  List of dicts: [{"label": ..., "reasoning": ...}]
        related_task_ids: List of existing task _ids this task is related to

    Returns:
        The task node's _id
    """
    print(f"\n[writer] Remembering task: '{task_label}'")

    # 1. Save the task node
    task_id = save_task(label=task_label, summary=task_summary)

    # 2. Save tools and link them
    for tool_name in (tools_used or []):
        tool_id = save_tool(label=tool_name)
        link_nodes(
            from_id=task_id, from_type=NODE_TASK,
            relation=REL_USED_TOOL,
            to_id=tool_id, to_type=NODE_TOOL
        )

    # 3. Save facts and link them
    for fact in (facts_learned or []):
        fact_id = save_fact(
            label=fact["label"],
            content=fact["content"],
            confidence=fact.get("confidence", 1.0)
        )
        link_nodes(
            from_id=task_id, from_type=NODE_TASK,
            relation=REL_LEARNED,
            to_id=fact_id, to_type=NODE_FACT
        )

    # 4. Save decisions and link them
    for decision in (decisions_made or []):
        decision_id = save_decision(
            label=decision["label"],
            reasoning=decision["reasoning"]
        )
        link_nodes(
            from_id=task_id, from_type=NODE_TASK,
            relation=REL_MADE_DECISION,
            to_id=decision_id, to_type=NODE_DECISION
        )

    # 5. Link to related past tasks
    for related_id in (related_task_ids or []):
        link_nodes(
            from_id=task_id, from_type=NODE_TASK,
            relation=REL_RELATED_TO,
            to_id=related_id, to_type=NODE_TASK
        )

    print(f"[writer] Task memory complete: '{task_label}'\n")
    return task_id
