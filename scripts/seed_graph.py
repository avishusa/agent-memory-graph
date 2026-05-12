import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.writer import remember_task

def seed():
    print("Seeding knowledge graph with sample agent memories...\n")

    # Memory 1 — a past task the agent completed
    task1_id = remember_task(
        task_label="Fix JWT login bug",
        task_summary="Debugged auth middleware. Found JWT expiry was set to 1h but refresh logic was missing.",
        tools_used=["read_file", "edit_file", "search_docs"],
        facts_learned=[
            {
                "label": "JWT expiry is 1 hour",
                "content": "The auth middleware sets JWT expiry to 3600 seconds. No refresh token logic exists.",
                "confidence": 1.0
            },
            {
                "label": "Auth middleware location",
                "content": "Auth logic lives in /src/middleware/auth.py",
                "confidence": 1.0
            }
        ],
        decisions_made=[
            {
                "label": "Added refresh token instead of extending expiry",
                "reasoning": "Extending JWT expiry is a security risk. Refresh tokens are the industry standard approach."
            }
        ]
    )

    # Memory 2 — a related task, linked to task 1
    task2_id = remember_task(
        task_label="Add token refresh endpoint",
        task_summary="Built /api/auth/refresh endpoint that validates refresh token and issues new JWT.",
        tools_used=["read_file", "edit_file", "run_tests"],
        facts_learned=[
            {
                "label": "Refresh endpoint is POST /api/auth/refresh",
                "content": "Accepts refresh_token in body, returns new access_token. Refresh tokens expire in 7 days.",
                "confidence": 1.0
            }
        ],
        decisions_made=[
            {
                "label": "Stored refresh tokens in Redis not MongoDB",
                "reasoning": "Refresh tokens need fast lookup and auto-expiry. Redis TTL handles this natively."
            }
        ],
        related_task_ids=[task1_id]
    )

    print(f"Seeded 2 tasks, linked together.")
    print(f"Task 1 ID: {task1_id}")
    print(f"Task 2 ID: {task2_id}")
    print("\nOpen MongoDB Atlas and check your 'nodes' and 'edges' collections.")

if __name__ == "__main__":
    seed()