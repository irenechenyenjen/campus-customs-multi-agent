# Campus Customs Agent Harness

## Database setup

- Original source: `hw5/data/campus_customs.db` (preserved and used as the reset source).
- Working copy: `hw5/data/campus_customs_new.db` (the database that MCP tools and the backend must update).
- The requested filename `campus_custims_new.db` is a typo; the correctly named `campus_customs_new.db` already exists and matches the original byte-for-byte.
- Current shop date from `desk.data_today`: `2026-08-31`.

## Tables and fields

| Table | Fields | Why it matters to the agent team |
|---|---|---|
| `cash_accounts` | `name` (TEXT, PK), `balance` (REAL), `date` (TEXT) | Shows available cash and prevents approved payments from creating a negative balance. |
| `desk` | `date_today` (TEXT), `notes` (TEXT) | Defines the shop's current date, which agents use to identify overdue work. |
| `inventory` | `sku` (TEXT, PK part), `name` (TEXT), `size` (TEXT, PK part), `qty` (INTEGER), `location` (TEXT) | Lets Inventory check stock by SKU and size and identify shortages and shelf locations. |
| `invoices` | `id` (INTEGER, PK), `vendor_id` (INTEGER), `amount` (REAL), `due_date` (TEXT), `status` (TEXT), `description` (TEXT) | Tracks vendor obligations; unpaid open invoices can block vendor shipments and require approval before payment. |
| `leases` | `id` (INTEGER, PK), `space_name` (TEXT), `landlord` (TEXT), `monthly_rent` (REAL), `next_due` (TEXT), `notes` (TEXT) | Gives Facilities the shop-space and rent information needed to handle lease tickets. |
| `payments` | `id` (INTEGER, PK), `kind` (TEXT), `ref_id` (INTEGER), `amount` (REAL), `account` (TEXT), `paid_at` (TEXT), `approved_by` (TEXT) | Provides the audit trail for human-approved outgoing payments and links them to invoices or other obligations. |
| `pricing` | `sku` (TEXT, PK), `unit_cost` (REAL), `list_price` (REAL) | Supports margin checks, discount decisions, and purchase-cost calculations. |
| `tickets` | `id` (INTEGER, PK), `type` (TEXT), `requester` (TEXT), `subject` (TEXT), `sku` (TEXT), `size` (TEXT), `qty` (INTEGER), `lease_id` (INTEGER), `invoice_id` (INTEGER), `status` (TEXT), `notes` (TEXT), `created_at` (TEXT) | The shared work board: Boss routes tickets and agents resolve them while preserving status and cross-table references. |
| `vendors` | `id` (INTEGER, PK), `name` (TEXT), `specialty` (TEXT), `lead_days` (INTEGER) | Identifies suitable vendors and their lead times for restocking or other operational work. |

## Open-ticket relationships

There are three open tickets:

1. Ticket `101` is a `customer_order` for one `CC-TEE-WHITE`, size `S`. It links to `inventory` by `(sku, size)`, where stock is currently `0`; it also references invoice `501` through `tickets.invoice_id`. Invoice `501` is an open, overdue `$840` invoice for a rush reprint from vendor `1`, Bulldog Print Co. Vendor `1` has a five-day lead time. This ticket therefore involves Customer Service, Inventory, Accounting, and the vendor-payment/shipment rule.
2. Ticket `102` is a `rent_notice` for lease `1`. It links to `leases.id`, where the Chapel Street shop rent is `$2,400` and the next due date is `2026-09-02`, two days after the shop date. Facilities handles the lease details; Accounting prepares any payment for human approval and records it in `payments` after approval.
3. Ticket `103` is a `price_override` for twenty `CC-HOOD-NAVY` hoodies in size `M`. It links to `inventory` by `(sku, size)` (currently `8` units) and to `pricing.sku`, where unit cost is `$22` and list price is `$58`. The requested quantity exceeds current stock, so Inventory must identify the shortfall; Accounting and the Boss should assess the discount and margin before any human approval.

## Agent-facing rules

- Use `desk.data_today` for overdue calculations.
- A vendor will not ship new product while it has an open unpaid invoice.
- Payments always require human approval, must update the relevant records, and must never make a cash account negative.
- Cash only leaves the modeled system; no revenue is recorded.
- Before a full resolution run, reset the working copy from the untouched original.
- Customer and vendor communications remain drafts on the board; do not send messages or make calls.

## MCP tools

The initial FastMCP server is in `hw5/mcp_server/server.py` and uses the working database `hw5/data/campus_customs_new.db`.

| Tool | Tables read | Ticket it helps unlock | Why it is the right tool |
|---|---|---|---|
| `check_inventory(sku, size)` | `inventory`, `pricing` | 101 and 103 | For ticket 101 it confirms that `CC-TEE-WHITE` size `S` is unavailable; for ticket 103 it confirms the hoodie quantity and supplies cost/list-price data needed to evaluate the bulk request. |
| `get_invoice_status(invoice_id)` | `invoices`, `vendors` | 101 | It follows ticket 101's `invoice_id` to show whether the reprint invoice is unpaid and identifies the vendor lead time that matters before restocking can ship. |
| `get_lease_details(lease_id)` | `leases`, `desk` | 102 | It follows ticket 102's `lease_id` and returns the rent obligation together with `desk.date_today`, allowing Facilities and Accounting to assess whether rent is due or overdue. |
| `list_open_tickets()` | `tickets` | 101, 102, 103 | It gives Boss the authoritative open work board so every unresolved ticket is routed. |
| `list_tickets()` | `tickets` | 101, 102, 103 | It gives the dashboard the authoritative status of every ticket, including any resolved tickets after a run. |
| `get_cash_account(account)` | `cash_accounts` | 101, 102, 103 | It gives Accounting the current balance before preparing any payment and prevents recommendations that would create a negative balance. |
| `find_restock_vendors(sku)` | `vendors`, `invoices` | 101, 103 | It returns vendor lead times and open-invoice blockers for the missing tee or hoodie shortfall, without inventing a supplier. |

## Agent team

- **Boss** reads the open ticket board, delegates to specialists, reconciles evidence, and makes final recommendations.
- **Inventory** checks SKU/size stock and finds restock vendors.
- **Accounting** checks invoices, cash, and pricing evidence and prepares approval-only payment or purchase recommendations.
- **Facilities** handles lease and rent work.
- **Customer Service** drafts customer messages; it never sends them.

All five agents use the OpenAI model `gpt-6-luna`, have delegation tools that invoke the target agent and return its result, and record loop starts, MCP lookups, delegations, and completions in append-only `output/audit_trail.json`. The backend uses FastMCP's stdio client, so shop facts are obtained through the MCP server rather than a second database layer.

## Safety and token limits

- Human approval is mandatory for payments, purchase orders, discounts, and external communications.
- Enforce cash-balance checks, invoice-status checks, vendor shipment blockers, and least-privilege tool access before writes are added.
- Keep customer/vendor messages as drafts; require a human to review recipients and content.
- Preserve an append-only audit trail with run IDs and step numbers; never silently overwrite prior runs.
- Bound runs by ticket count, delegation depth, tool-call count, and model output tokens; stop on repeated delegation or missing database evidence.

## Backend routes

- `GET /tickets` — IRL: refresh the work board; returns all three tickets with their current open/resolved status.
- `POST /tickets/{ticket_id}/run` — IRL: ask Boss to work one ticket; runs the agent team while leaving cash and records unchanged until approval.
- `GET /events?limit=100` — IRL: refresh the activity feed; returns recent append-only agent events, including agent actions and MCP tools.
- `POST /approvals` — IRL: apply a human-approved payment or purchase; checks cash, updates the payment/invoice records, and refuses negative balances.
- `GET /cash` — IRL: show the checking account balance from `cash_accounts`.
- `POST /reset` — IRL: start a fresh exercise; copies the untouched original database over the working database.

## Problem 9 resolution record

- The working database was reset from the untouched original before the final run; starting checking balance was `$3,400.00`.
- Tickets `101`, `102`, and `103` end with status `resolved` in `campus_customs_new.db`.
- No human payment or purchase approval was given. Ticket 101's `$840` invoice, ticket 102's `$2,400` rent, and ticket 103's restock/discount decision therefore caused `$0.00` cash movement.
- Ending checking balance is `$3,400.00`, matching `cash_accounts.balance` in the working database.
- Detailed results are in `output/resolved_tickets.json`; the visual resolved-board snapshot is `output/resolved_board.html`; the ticket comparison is in `output/desk_tickets.html`.
- `output/audit_trail.json` preserves the real run records, including the failed/aborted exploratory delegation attempt. The final outcome records are appended rather than replacing prior entries.
