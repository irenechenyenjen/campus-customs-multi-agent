"""Read-only MCP tools for the Campus Customs operations team."""

from pathlib import Path
import sqlite3
from typing import Any

from fastmcp import FastMCP


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "data" / "campus_customs_new.db"

mcp = FastMCP("Campus Customs MCP")


def _fetch_one(query: str, parameters: tuple[Any, ...]) -> dict[str, Any] | None:
    """Run a parameterized read query against the working database."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(query, parameters).fetchone()
        return dict(row) if row is not None else None


@mcp.tool()
def check_inventory(sku: str, size: str) -> dict[str, Any]:
    """Return stock and pricing for one SKU and size, including the requested ticket context."""
    inventory = _fetch_one(
        """
        SELECT sku, name, size, qty, location
        FROM inventory
        WHERE sku = ? AND size = ?
        """,
        (sku, size),
    )
    pricing = _fetch_one(
        """
        SELECT sku, unit_cost, list_price
        FROM pricing
        WHERE sku = ?
        """,
        (sku,),
    )
    return {"inventory": inventory, "pricing": pricing}


@mcp.tool()
def get_invoice_status(invoice_id: int) -> dict[str, Any] | None:
    """Return an invoice and its vendor details so ticket 101 can determine payment and shipment blockers."""
    return _fetch_one(
        """
        SELECT invoices.id, invoices.vendor_id, invoices.amount, invoices.due_date,
               invoices.status, invoices.description, vendors.name AS vendor_name,
               vendors.specialty, vendors.lead_days
        FROM invoices
        LEFT JOIN vendors ON vendors.id = invoices.vendor_id
        WHERE invoices.id = ?
        """,
        (invoice_id,),
    )


@mcp.tool()
def get_lease_details(lease_id: int) -> dict[str, Any] | None:
    """Return lease and current shop date so ticket 102 can assess the rent notice."""
    return _fetch_one(
        """
        SELECT leases.id, leases.space_name, leases.landlord, leases.monthly_rent,
               leases.next_due, leases.notes, desk.date_today
        FROM leases
        CROSS JOIN desk
        WHERE leases.id = ?
        """,
        (lease_id,),
    )


@mcp.tool()
def list_open_tickets() -> list[dict[str, Any]]:
    """Return the open ticket board so Boss can route every unresolved ticket."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute("SELECT * FROM tickets WHERE status = 'open' ORDER BY id")]


@mcp.tool()
def list_tickets() -> list[dict[str, Any]]:
    """Return all tickets and their current status for the dashboard board."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute("SELECT * FROM tickets ORDER BY id")]


@mcp.tool()
def get_cash_account(account: str = "checking") -> dict[str, Any] | None:
    """Return current cash so Accounting can reject payments that would go negative."""
    return _fetch_one("SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,))


@mcp.tool()
def find_restock_vendors(sku: str) -> list[dict[str, Any]]:
    """Return vendors whose specialty can restock the requested SKU, including lead times and invoice blockers."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute("""
            SELECT vendors.id, vendors.name, vendors.specialty, vendors.lead_days,
                   invoices.id AS open_invoice_id, invoices.amount AS open_invoice_amount
            FROM vendors LEFT JOIN invoices ON invoices.vendor_id = vendors.id AND invoices.status = 'open'
            WHERE (? LIKE 'CC-HOOD-%' AND vendors.specialty = 'apparel reprint')
               OR (? LIKE 'CC-TEE-%' AND vendors.specialty = 'apparel reprint')
               OR (? LIKE 'CC-MUG-%' AND vendors.specialty = 'mugs and small goods')
            ORDER BY vendors.lead_days
        """, (sku, sku, sku))]


if __name__ == "__main__":
    mcp.run(transport="stdio")
