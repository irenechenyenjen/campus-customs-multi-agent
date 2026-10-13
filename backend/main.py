"""FastAPI control plane for the Campus Customs agent desk."""
import asyncio
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from .audit import AUDIT_PATH
    from .mcp_tools import call_mcp
    from .team import TeamDeps, run_agent
except ImportError:
    from audit import AUDIT_PATH
    from mcp_tools import call_mcp
    from team import TeamDeps, run_agent

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_DB = PROJECT_ROOT / "data" / "campus_customs.db"
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"

app = FastAPI(title="Campus Customs Operations API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://localhost:5173", "https://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApprovalRequest(BaseModel):
    kind: str = Field(pattern="^(payment|purchase)$")
    ref_id: int
    amount: float = Field(gt=0)
    account: str = "checking"
    approved_by: str = Field(min_length=1)


def db_read(query: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with sqlite3.connect(WORKING_DB) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query, parameters)]


@app.get("/tickets")
async def tickets() -> list[dict[str, Any]]:
    """Return every ticket and its current open/resolved status."""
    return await call_mcp("list_tickets")


@app.post("/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int) -> dict[str, Any]:
    """Run Boss for one ticket; agents recommend actions but do not mutate cash."""
    rows = [ticket for ticket in await call_mcp("list_tickets") if ticket["id"] == ticket_id]
    if not rows:
        raise HTTPException(404, "Ticket not found")
    deps = TeamDeps()
    routing = {
        101: "Start with Inventory; then delegate Accounting for invoice/cash evidence and Customer Service only for a draft if useful.",
        102: "Start with Facilities. Use lease_id=1 with get_lease_details to verify the lease; then delegate Accounting for cash/payment preparation if useful.",
        103: "Start with Inventory. Use sku=CC-HOOD-NAVY, size=M, and requested quantity=20 with check_inventory and find_restock_vendors; then delegate Accounting for margin/cash evidence and Customer Service only for a draft if useful.",
    }
    prompt = routing.get(ticket_id, "Delegate only to the specialists needed.") + " Do not invent a specialist role, and do not delegate beyond the named five roles. Ticket data from MCP: " + json.dumps(rows[0], default=str)
    result = await run_agent("boss", prompt, deps)
    with sqlite3.connect(WORKING_DB) as connection:
        connection.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (ticket_id,))
    return {"ticket_id": ticket_id, "agent_output": result, "run_id": deps.run_id}


@app.get("/events")
async def events(limit: int = Query(100, ge=1, le=500)) -> list[dict[str, Any]]:
    """Return recent append-only agent events for dashboard refreshes."""
    if not AUDIT_PATH.exists():
        return []
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data[-limit:]


@app.post("/approvals")
async def approve(request: ApprovalRequest) -> dict[str, Any]:
    """Apply an explicitly human-approved payment/purchase without allowing negative cash."""
    with sqlite3.connect(WORKING_DB) as connection:
        connection.row_factory = sqlite3.Row
        account = connection.execute("SELECT name, balance, date FROM cash_accounts WHERE name = ?", (request.account,)).fetchone()
        if account is None:
            raise HTTPException(404, "Cash account not found")
        if account["balance"] < request.amount:
            raise HTTPException(409, "Payment refused: insufficient cash")
        if request.kind == "payment":
            invoice = connection.execute("SELECT id, amount, status FROM invoices WHERE id = ?", (request.ref_id,)).fetchone()
            if invoice is None:
                raise HTTPException(404, "Invoice not found")
            if invoice["status"] != "open":
                raise HTTPException(409, "Invoice is not open")
        else:
            invoice = connection.execute("SELECT id, amount, status FROM invoices WHERE id = ?", (request.ref_id,)).fetchone()
            if invoice is None or invoice["status"] != "open":
                raise HTTPException(409, "Purchase must reference an open invoice")
        paid_at = db_read("SELECT date_today FROM desk")[0]["date_today"]
        connection.execute("UPDATE cash_accounts SET balance = balance - ? WHERE name = ?", (request.amount, request.account))
        connection.execute("INSERT INTO payments(kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)", (request.kind, request.ref_id, request.amount, request.account, paid_at, request.approved_by))
        connection.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (request.ref_id,))
        new_balance = connection.execute("SELECT balance FROM cash_accounts WHERE name = ?", (request.account,)).fetchone()[0]
    return {"status": "approved_and_applied", "kind": request.kind, "ref_id": request.ref_id, "amount": request.amount, "new_balance": new_balance}


@app.get("/cash")
async def cash() -> dict[str, Any] | None:
    """Return the current checking balance."""
    return await call_mcp("get_cash_account", {"account": "checking"})


@app.post("/reset")
async def reset() -> dict[str, str]:
    """Restore the working database from the untouched original database."""
    def restore_database() -> None:
        with sqlite3.connect(ORIGINAL_DB) as source, sqlite3.connect(WORKING_DB) as destination:
            source.backup(destination)
    await asyncio.to_thread(restore_database)
    return {"status": "reset", "database": str(WORKING_DB)}
