# Campus Customs Multi-Agent Operations

Campus Customs is a database-backed operations desk with a FastMCP server, a PydanticAI agent team, a FastAPI backend, and a React/Vite dashboard.

## Project layout

```text
hw5/
├── AI_prompts.md
├── .env.example
├── .gitignore
├── .mcp.json
├── backend/
├── data/
│   ├── campus_customs.db
│   └── campus_customs_new.db
├── frontend/
├── mcp_server/
└── output/
```

The original database is `data/campus_customs.db`. The agents and tools use `data/campus_customs_new.db` as the working copy. Never modify the original when resetting a run.

## Setup

1. Copy `.env.example` to `.env` and set `PORTKEY_API_KEY`. Never commit `.env`.
2. Install Python dependencies: `pip install -r requirements.txt`.
3. Install frontend dependencies: `cd frontend` then `npm install`.

## Run the app

Start the MCP server when using an MCP client:

```text
python mcp_server/server.py
```

Start the FastAPI backend from `backend/`:

```text
uvicorn main:app --reload --port 8000
```

Start the React board from `frontend/`:

```text
npm run dev
```

Open `http://127.0.0.1:5173`. The backend is at `http://127.0.0.1:8000`.

## Clean run procedure

Before a full three-ticket run, reset the working database from the original. Use the backend `POST /reset` route, or copy `data/campus_customs.db` over `data/campus_customs_new.db`. Confirm the starting checking balance before running tickets 101, 102, and 103.

Agents may prepare recommendations, drafts, and payment requests. Human approval is required before a payment or purchase changes cash. Customer and vendor communications remain drafts.

## Outputs

`output/harness.md` documents the tables, MCP tools, agents, API routes, dashboard, safety rules, and run results. `output/desk_tickets.html` is the expected/actual planning board. `output/resolved_tickets.json` and `output/resolved_board.html` contain the final run record and static board snapshot.
