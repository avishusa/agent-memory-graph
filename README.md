# Agent Memory Graph

An AI agent with persistent memory powered by a knowledge graph in MongoDB.

The agent remembers tasks it has performed, tools it used, facts it learned,
and decisions it made — and uses that memory to make smarter decisions on
future tasks.

## Stack
- **MongoDB Atlas** — knowledge graph storage
- **Google Gemini Flash** — LLM agent
- **Python** — core language

## Setup
1. Clone the repo
2. Copy `.env.example` to `.env` and fill in your keys
3. `pip install -r requirements.txt`
4. `python scripts/seed_graph.py`

## Architecture
See `/graph` for the knowledge graph layer.
See `/agent` for the agent layer.