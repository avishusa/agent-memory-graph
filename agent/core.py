import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

from graph.reader import get_full_context
from graph.writer import remember_task
from agent.tools import get_tools_description, simulate_tool_use, AVAILABLE_TOOLS

load_dotenv()

# ─── Configure Gemini client ───────────────────────────────────
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-lite"

# ─── Prompt builders ───────────────────────────────────────────

def build_system_prompt() -> str:
    return f"""You are an expert AI software engineering agent with persistent memory.

Before responding to any task, you are given context from your memory graph —
facts you have learned, decisions you have made, and tools you have used in the past.
Use this memory to give smarter, more consistent responses.

{get_tools_description()}

After completing a task you MUST respond in this exact JSON format:
{{
  "response": "Your detailed response to the task here",
  "tools_used": ["tool_name_1", "tool_name_2"],
  "facts_learned": [
    {{"label": "short fact title", "content": "detailed fact content", "confidence": 0.95}}
  ],
  "decisions_made": [
    {{"label": "short decision title", "reasoning": "why you made this decision"}}
  ],
  "keywords": ["keyword1", "keyword2"]
}}

Rules:
- tools_used must only contain tools from the available tools list
- facts_learned should capture anything genuinely useful to remember
- decisions_made should capture any non-obvious choices and why
- keywords are 1-3 words that describe the core topic of this task
- Be specific and precise in facts and decisions — vague memories are useless
"""


def build_task_prompt(task: str, context: dict) -> str:
    """
    Builds the user-facing prompt by combining the task
    with retrieved memory context from the graph.
    """
    prompt_parts = [f"## Task\n{task}\n"]

    if context["facts"]:
        prompt_parts.append("## What you remember (from past tasks)")
        for fact in context["facts"]:
            confidence = fact["properties"].get("confidence", 1.0)
            prompt_parts.append(
                f"- [{fact['label']}] {fact['properties']['content']} "
                f"(confidence: {confidence})"
            )

    if context["decisions"]:
        prompt_parts.append("\n## Past decisions relevant to this")
        for decision in context["decisions"]:
            prompt_parts.append(
                f"- [{decision['label']}] {decision['properties']['reasoning']}"
            )

    if context["tasks"]:
        prompt_parts.append("\n## Similar tasks you have handled before")
        for past_task in context["tasks"]:
            prompt_parts.append(
                f"- {past_task['label']}: {past_task['properties'].get('summary', '')}"
            )

    if context["tools"]:
        tool_names = [t["label"] for t in context["tools"]]
        prompt_parts.append(
            f"\n## Tools you used on similar tasks\n{', '.join(tool_names)}"
        )

    prompt_parts.append("\nNow complete the task. Respond in the required JSON format.")
    return "\n\n".join(prompt_parts)


# ─── Response parser ───────────────────────────────────────────

def parse_agent_response(raw: str) -> dict:
    """
    Parses Gemini's JSON response safely.
    Gemini sometimes wraps JSON in markdown code blocks — we handle that.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[agent] Warning: could not parse JSON response: {e}")
        return {
            "response": raw,
            "tools_used": [],
            "facts_learned": [],
            "decisions_made": [],
            "keywords": []
        }


# ─── Main agent function ───────────────────────────────────────

def run_agent(task: str, context_keyword: str = None) -> str:
    """
    The main entry point for the agent.

    Args:
        task:            The task description from the user
        context_keyword: Keyword to search memory graph with.
                         If None, uses first word of task.

    Returns:
        The agent's response as a string
    """
    print(f"\n{'='*60}")
    print(f"[agent] New task: {task}")
    print(f"{'='*60}")

    # ── Step 1: retrieve memory context ───────────────────────
    keyword = context_keyword or task.split()[0].lower()
    context = get_full_context(keyword)

    has_memory = any([
        context["facts"],
        context["decisions"],
        context["tasks"]
    ])

    if has_memory:
        print(f"[agent] Memory found — agent will use past knowledge")
    else:
        print(f"[agent] No prior memory — agent starts fresh")

    # ── Step 2: build prompt and call Gemini ──────────────────
    system_prompt = build_system_prompt()
    task_prompt = build_task_prompt(task, context)

    print(f"[agent] Calling Gemini ({MODEL})...")

    response = client.models.generate_content(
        model=MODEL,
        contents=f"{system_prompt}\n\n{task_prompt}",
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=1500,
        )
    )

    raw_text = response.text

    # ── Step 3: parse the structured response ─────────────────
    parsed = parse_agent_response(raw_text)

    # ── Step 4: simulate tool use ─────────────────────────────
    for tool in parsed.get("tools_used", []):
        if tool in AVAILABLE_TOOLS:
            simulate_tool_use(tool, task)

    # ── Step 5: write memory back to graph ────────────────────
    related_ids = [t["_id"] for t in context.get("tasks", [])]

    remember_task(
        task_label=task[:80],
        task_summary=parsed["response"][:500],
        tools_used=parsed.get("tools_used", []),
        facts_learned=parsed.get("facts_learned", []),
        decisions_made=parsed.get("decisions_made", []),
        related_task_ids=related_ids
    )

    print(f"\n[agent] Task complete. Memory updated.")
    return parsed["response"]