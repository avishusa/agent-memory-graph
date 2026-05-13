from datetime import datetime, timezone
from uuid import uuid4


# ─── Node Types ───────────────────────────────────────────────
NODE_TASK     = "Task"
NODE_TOOL     = "Tool"
NODE_FACT     = "Fact"
NODE_DECISION = "Decision"

VALID_NODE_TYPES = {NODE_TASK, NODE_TOOL, NODE_FACT, NODE_DECISION}


# ─── Edge (Relation) Types ────────────────────────────────────
REL_USED_TOOL    = "USED_TOOL"
REL_LEARNED      = "LEARNED"
REL_MADE_DECISION = "MADE_DECISION"
REL_RELATED_TO   = "RELATED_TO"
REL_DEPENDS_ON   = "DEPENDS_ON"

VALID_RELATIONS = {
    REL_USED_TOOL,
    REL_LEARNED,
    REL_MADE_DECISION,
    REL_RELATED_TO,
    REL_DEPENDS_ON,
}


# ─── Allowed edges: which types can connect to which ──────────
ALLOWED_EDGES = {
    REL_USED_TOOL:     (NODE_TASK, NODE_TOOL),
    REL_LEARNED:       (NODE_TASK, NODE_FACT),
    REL_MADE_DECISION: (NODE_TASK, NODE_DECISION),
    REL_RELATED_TO:    (NODE_TASK, NODE_TASK),
    REL_DEPENDS_ON:    (NODE_TASK, NODE_FACT),
}


# ─── Factory functions ────────────────────────────────────────
def make_node(node_type: str, label: str, properties: dict = None) -> dict:
    """
    Create a well-formed node document ready to insert into MongoDB.
    Raises ValueError if node_type is not valid.
    """
    if node_type not in VALID_NODE_TYPES:
        raise ValueError(f"Invalid node type '{node_type}'. Must be one of {VALID_NODE_TYPES}")

    return {
        "_id": str(uuid4()),
        "type": node_type,
        "label": label,
        "properties": {
            **(properties or {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    }


def make_edge(
    from_id: str,
    from_type: str,
    relation: str,
    to_id: str,
    to_type: str,
    properties: dict = None
) -> dict:
    """
    Create a well-formed edge document ready to insert into MongoDB.
    Validates that the from/to types are allowed for this relation.
    """
    if relation not in VALID_RELATIONS:
        raise ValueError(f"Invalid relation '{relation}'. Must be one of {VALID_RELATIONS}")

    allowed_from, allowed_to = ALLOWED_EDGES[relation]
    if from_type != allowed_from or to_type != allowed_to:
        raise ValueError(
            f"Relation '{relation}' requires {allowed_from} → {allowed_to}, "
            f"got {from_type} → {to_type}"
        )

    return {
        "_id": str(uuid4()),
        "from_id": from_id,
        "from_type": from_type,
        "relation": relation,
        "to_id": to_id,
        "to_type": to_type,
        "properties": {
            **(properties or {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    }