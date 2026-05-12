import sys
import os
from db.indexes import create_indexes
from agent.core import run_agent

def main():
    # Ensure indexes exist every time the app starts
    # This is idempotent — no cost if indexes already exist
    create_indexes()

    print("\nAgent Memory Graph — Interactive Mode")
    print("Type a task and press Enter. Type 'quit' to exit.\n")

    while True:
        task = input("Task > ").strip()

        if not task:
            continue
        if task.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break

        words = task.lower().split()
        keyword = words[1] if len(words) > 1 else words[0]

        response = run_agent(task=task, context_keyword=keyword)

        print(f"\n{'─'*60}")
        print(f"Agent: {response}")
        print(f"{'─'*60}\n")

if __name__ == "__main__":
    main()