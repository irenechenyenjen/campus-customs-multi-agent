"""Five connected PydanticAI agents for Campus Customs."""
import asyncio
import os
from pathlib import Path
from typing import Literal
from uuid import uuid4
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext, UsageLimits
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
try:
    from .audit import append_audit
    from .mcp_tools import call_mcp
except ImportError:
    from audit import append_audit
    from mcp_tools import call_mcp

MODEL_NAME = "gpt-6-luna"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")
PORTKEY_KEY = os.getenv("PORTKEY_API_KEY")

if PORTKEY_KEY:
    _client = AsyncOpenAI(
        api_key=PORTKEY_KEY,
        base_url="https://api.portkey.ai/v1",
        default_headers={"x-portkey-api-key": PORTKEY_KEY},
    )
    MODEL = OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=_client))
else:
    MODEL = f"openai-chat:{MODEL_NAME}"
PROMPTS = Path(__file__).parent / "prompts"

class TeamDeps:
    def __init__(self): self.run_id, self.step, self.delegation_depth = str(uuid4()), 0, 0
    def record(self, agent, action, ticket_id=None, tool=None, result_summary=""):
        self.step += 1
        append_audit({"run_id": self.run_id, "step": self.step, "agent": agent, "action": action, "ticket_id": ticket_id, "tool": tool, "result_summary": result_summary})

def make_agent(role):
    return Agent(MODEL, deps_type=TeamDeps, model_settings={"openai_reasoning_effort": "none"}, system_prompt=(PROMPTS / f"{role}.txt").read_text(encoding="utf-8"), output_type=str)

boss = make_agent("boss")
inventory = make_agent("inventory")
accounting = make_agent("accounting")
facilities = make_agent("facilities")
customer_service = make_agent("customer_service")
AGENTS = {"boss": boss, "inventory": inventory, "accounting": accounting, "facilities": facilities, "customer_service": customer_service}

@boss.tool
async def list_open_tickets(ctx: RunContext[TeamDeps]):
    result = await call_mcp("list_open_tickets")
    ctx.deps.record("boss", "MCP lookup", tool="list_open_tickets", result_summary=str(result))
    return result

@inventory.tool
async def check_inventory(ctx: RunContext[TeamDeps], sku: str, size: str):
    result = await call_mcp("check_inventory", {"sku": sku, "size": size})
    ctx.deps.record("inventory", "MCP lookup", tool="check_inventory", result_summary=str(result))
    return result

@inventory.tool
async def find_restock_vendors(ctx: RunContext[TeamDeps], sku: str):
    result = await call_mcp("find_restock_vendors", {"sku": sku})
    ctx.deps.record("inventory", "MCP lookup", tool="find_restock_vendors", result_summary=str(result))
    return result

@accounting.tool
async def get_invoice_status(ctx: RunContext[TeamDeps], invoice_id: int):
    result = await call_mcp("get_invoice_status", {"invoice_id": invoice_id})
    ctx.deps.record("accounting", "MCP lookup", tool="get_invoice_status", result_summary=str(result))
    return result

@accounting.tool
async def get_cash_account(ctx: RunContext[TeamDeps], account: str = "checking"):
    result = await call_mcp("get_cash_account", {"account": account})
    ctx.deps.record("accounting", "MCP lookup", tool="get_cash_account", result_summary=str(result))
    return result

@facilities.tool
async def get_lease_details(ctx: RunContext[TeamDeps], lease_id: int):
    result = await call_mcp("get_lease_details", {"lease_id": lease_id})
    ctx.deps.record("facilities", "MCP lookup", tool="get_lease_details", result_summary=str(result))
    return result

def add_delegation(agent, role):
    async def delegate(ctx: RunContext[TeamDeps], task: str, ticket_id: int, target: Literal["boss", "inventory", "accounting", "facilities", "customer_service"]):
        if ctx.deps.delegation_depth >= 1:
            ctx.deps.record(role, "delegation blocked", ticket_id, result_summary="Maximum specialist delegation depth reached.")
            return {"delegated_to": target, "ticket_id": ticket_id, "result": "Delegation stopped at the configured one-level specialist limit."}
        ctx.deps.record(role, "delegated task", ticket_id, result_summary=f"delegated to {target}: {task}")
        if target not in AGENTS:
            return f"Delegation refused: unknown agent {target}."
        ctx.deps.delegation_depth += 1
        try:
            result = await run_agent(target, f"Ticket {ticket_id}: {task}. Do not delegate further; use your assigned MCP tools and return your evidence.", ctx.deps)
        finally:
            ctx.deps.delegation_depth -= 1
        return {"delegated_to": target, "ticket_id": ticket_id, "result": result}
    agent.tool(delegate)

for _role, _agent in AGENTS.items(): add_delegation(_agent, _role)

async def run_agent(role, prompt, deps):
    deps.record(role, "agent loop started", result_summary=prompt)
    result = await AGENTS[role].run(prompt, deps=deps, usage_limits=UsageLimits(request_limit=8, tool_calls_limit=12))
    deps.record(role, "agent loop completed", result_summary=str(result.output))
    return result.output

async def run_team(prompt):
    deps = TeamDeps()
    return await run_agent("boss", prompt, deps)

if __name__ == "__main__":
    print(asyncio.run(run_team("Review the open tickets and delegate each to the right specialists.")))
