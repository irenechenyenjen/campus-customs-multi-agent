from typing import Literal
from pydantic import BaseModel, Field

Role = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]

class Ticket(BaseModel):
    id: int
    type: str
    requester: str
    subject: str
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    lease_id: int | None = None
    invoice_id: int | None = None
    status: str
    notes: str | None = None

class AgentStep(BaseModel):
    run_id: str
    step: int
    agent: Role
    action: str
    ticket_id: int | None = None
    tool: str | None = None
    result_summary: str

class Decision(BaseModel):
    ticket_id: int
    decision: str
    rationale: str
    needs_human_approval: bool = True
    delegated_to: list[Role] = Field(default_factory=list)
