# Campus Customs MCP Server

This FastMCP server provides the shared, database-backed read tools that the Campus Customs agents use to investigate open tickets. It uses the working database at `hw5/data/campus_customs_new.db`; the original `campus_customs.db` remains untouched as the reset source.

The implementation imports `FastMCP` from the standalone `fastmcp` package.

The server currently exposes three read-only tools:

- `check_inventory(sku, size)`: reads `inventory` and `pricing` to check stock, location, cost, and list price for the product needed by tickets 101 and 103.
- `get_invoice_status(invoice_id)`: reads `invoices` and `vendors` to determine the unpaid invoice and vendor shipment details blocking ticket 101.
- `get_lease_details(lease_id)`: reads `leases` and `desk` to evaluate the rent amount, due date, and shop date for ticket 102.
- `list_open_tickets()`: reads `tickets` so Boss can route every open ticket.
- `list_tickets()`: reads `tickets` so the dashboard can show all ticket statuses.
- `get_cash_account(account)`: reads `cash_accounts` so Accounting can enforce no-negative-cash payments.
- `find_restock_vendors(sku)`: reads `vendors` and open `invoices` to identify lead times and shipment blockers for shortages.

More tools can be added as later problems introduce database updates and approval workflows. The server is intentionally not connected or run in Problem 3.

The backend connects to this server through FastMCP's stdio client; agents do not query SQLite directly. Delegation is performed by the Boss and specialist agents through their PydanticAI delegation tools.
