# Agent Memory Graph

An AI agent that remembers — powered by a knowledge graph in MongoDB.

Most AI agents are stateless. Every conversation starts from zero.
This project gives an agent **persistent memory** using a knowledge graph:
past tasks, tools used, facts learned, and decisions made are all stored
as interconnected nodes and edges in MongoDB — and retrieved before every
new task so the agent gets smarter over time.

Built as a production-grade POC to demonstrate knowledge graph design,
graph traversal with `$graphLookup`, and the memory read/write loop
that underlies real-world AI agent systems.

---

## What it does

```
User gives task
      │
      ▼
[1] Query knowledge graph for relevant past context
      │  "Have I seen something like this before?"
      ▼
[2] Inject retrieved memory into LLM prompt
      │  "Here's what you remember about auth systems..."
      ▼
[3] Gemini reasons and responds
      │
      ▼
[4] Parse response — extract facts, decisions, tools used
      │
      ▼
[5] Write new memories back to the graph
      │  "Remember this for next time"
      ▼
Agent is smarter for the next task
```

Each run enriches the graph. The agent compounds knowledge over time.

---

## Architecture

```
agent-memory-graph/
│
├── graph/                  # Knowledge graph layer (no LLM dependency)
│   ├── schema.py           # Node & edge type definitions + factory functions
│   ├── writer.py           # Write nodes and edges to MongoDB
│   └── reader.py           # Query graph with $graphLookup traversal
│
├── agent/                  # AI agent layer
│   ├── core.py             # Memory read → Gemini → memory write loop
│   └── tools.py            # Tool registry the agent can use
│
├── db/                     # Database layer
│   ├── connection.py       # MongoDB singleton with fail-fast validation
│   └── indexes.py          # Index setup for all query patterns
│
├── scripts/                # Utilities
│   ├── seed_graph.py       # Seed initial memories for testing
│   └── test_reader.py      # Verify graph queries + index usage
│
└── main.py                 # Interactive agent runner
```

### Graph schema

**Node types**

| Type | What it represents | Example |
|---|---|---|
| `Task` | A job the agent completed | "Fix JWT login bug" |
| `Tool` | A tool the agent used | "read_file", "search_docs" |
| `Fact` | Something the agent learned | "Auth uses JWT, expires in 1h" |
| `Decision` | A choice the agent made and why | "Used refresh tokens over extending expiry" |

**Edge types**

| Relation | From → To | Meaning |
|---|---|---|
| `USED_TOOL` | Task → Tool | This task used this tool |
| `LEARNED` | Task → Fact | This task produced this fact |
| `MADE_DECISION` | Task → Decision | This task involved this decision |
| `RELATED_TO` | Task → Task | These tasks are connected |
| `DEPENDS_ON` | Task → Fact | This task relied on this fact |

### Key design decisions

**Two collections — `nodes` and `edges`**
All entities live in one `nodes` collection regardless of type. All
relationships live in one `edges` collection. This lets MongoDB's
`$graphLookup` traverse the entire graph in a single aggregation pipeline.

**Application-layer schema enforcement**
MongoDB is schemaless — but our code isn't. `schema.py` validates every
node and edge before it touches the database. Invalid edges (wrong types,
unsupported relations) raise immediately rather than silently corrupting
the graph.

**Upsert for tools, insert for facts**
Tools are reusable entities (`read_file` exists once, linked to many tasks).
Facts are contextual — the same fact learned in two different tasks is
two data points. This asymmetry is intentional.

**Fail-fast database connection**
`MongoClient` is lazy by default — it won't actually connect until the
first query. We force a `ping` at startup so misconfigured environments
fail immediately with a clear error, not silently mid-operation.

---

## Stack

| Layer | Technology | Why |
|---|---|---|
| Database | MongoDB Atlas M0 (free) | Flexible document model + `$graphLookup` |
| LLM | Google Gemini 2.5 Flash-Lite (free) | Generous free tier, fast |
| Language | Python 3.10+ | Industry standard for AI engineering |
| DB driver | PyMongo | Official MongoDB Python driver |
| LLM SDK | google-genai | Official Google Gen AI SDK |

---

## Setup

### Prerequisites
- Python 3.10+
- MongoDB Atlas account (free at cloud.mongodb.com)
- Google AI Studio account (free at aistudio.google.com)

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/agent-memory-graph.git
cd agent-memory-graph
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```
GEMINI_API_KEY=your-gemini-api-key
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME=agent_memory
```

### 3. Seed initial memories

```bash
python scripts/seed_graph.py
```

### 4. Run the agent

```bash
python main.py
```

---

## How the memory works

Try running these three tasks in order and watch the agent use memory
from earlier tasks in its later responses:

```
Task > Help me fix an authentication bug in my Python API
Task > I need to add a logout endpoint to my auth system
Task > Review the security of our JWT implementation
```

On the second and third tasks you will see:
```
[agent] Memory found — agent will use past knowledge
[reader] Context built — 2 tasks, 4 facts, 2 decisions, 3 tools
```

The agent is querying its own knowledge graph before responding.

---

## MongoDB highlights

### `$graphLookup` traversal

Finding tasks related to a given task, up to N hops deep:

```python
pipeline = [
    {"$match": {"from_id": task_id, "relation": "RELATED_TO"}},
    {"$graphLookup": {
        "from": "edges",
        "startWith": "$to_id",
        "connectFromField": "to_id",
        "connectToField": "from_id",
        "restrictSearchWithMatch": {"relation": "RELATED_TO"},
        "as": "related_chain",
        "maxDepth": 2,
        "depthField": "hop_depth"
    }}
]
```

### Indexes

Every query pattern has a supporting index:

```
nodes: idx_nodes_type, idx_nodes_type_label, idx_nodes_text_search
edges: idx_edges_from_id, idx_edges_to_id,
       idx_edges_from_relation, idx_edges_to_relation
```

No collection scans in production query paths.

---

## What I learned building this

- How to model a knowledge graph in a document database
- The tradeoff between embedded relationships vs separate edge collections
- How `$graphLookup` enables recursive graph traversal without application loops
- Why indexes must be designed around query patterns, not table structure
- How to build a memory read/write loop for AI agents
- Production patterns: singleton connections, fail-fast validation,
  idempotent index creation, exponential backoff on rate limits

---

## Potential extensions

- **Vector similarity search** — replace keyword search with MongoDB Atlas
  Vector Search for semantic memory retrieval
- **Memory decay** — add a `confidence` decay function so old facts
  gradually matter less
- **Graph visualization** — export the graph to a visualization tool
  like Gephi or D3.js
- **Multi-agent memory** — multiple agents sharing the same graph,
  each contributing and reading memories