# OrderOps AI — Autonomous Order Triage & Resolution Agent

An e-commerce backend agent that automatically handles out-of-stock situations after checkout. Instead of auto-cancelling an order when an item is unavailable, the agent checks inventory, negotiates an alternative product with the customer by email, and falls back to a refund if the customer doesn't accept — all orchestrated as a LangGraph state machine with real pause/resume.

Built as a learning/portfolio project to practice production-style backend architecture: FastAPI, LangGraph, SQLAlchemy, Alembic, and real third-party integrations (Postgres, email).

**Live demo:** https://order-ops-ai.vercel.app/

---

## How it works

1. An order comes in via `POST /orders` (or the one-click demo flow — see below).
2. A LangGraph state machine runs:
   - **fraud_check** — rule-based risk scoring. Order value over $100 adds risk, no phone number on file adds risk, quantity over 5 adds risk. If the combined score crosses a threshold, the order is flagged for manual review and the graph ends there — it never reaches negotiation.
   - **inventory_check** — checks stock for every item in the order.
   - **negotiate** — for any out-of-stock item(s), finds an alternative product via keyword matching against product names and emails the customer a bundled offer (all out-of-stock items in one email) with **Accept** / **Decline** links per item.
   - **await_response** — the graph genuinely pauses here using a Postgres-backed LangGraph checkpointer (`PostgresSaver`), keyed by `thread_id = order_id`. This is a real interrupt/resume, not polling — the process can restart and the paused state survives, because it's persisted in Postgres, not memory.
   - **finalize** — updates the order status based on the customer's decision: accepted offers move to `fulfilled`/`updated`, declines move to `refunded`.
3. Every order and its current state is visible on a live dashboard at `/dashboard`.

## Project structure

```
app/
├── main.py            # FastAPI app, all routes
├── database.py        # SQLAlchemy engine/session setup
├── models.py           # Customer, Product, Order, OrderItem, NegotiationOffer
├── schemas.py          # Pydantic request/response models
├── graph/
│   ├── state.py         # LangGraph state schema
│   └── graph.py          # Node definitions + graph wiring
├── services/
│   └── email.py          # Brevo email sending (negotiation offers)
└── static/
    └── index.html         # Single-file dashboard (no build step)
alembic/                # DB migrations
scripts/                # seed.py, test_graph.py, test_e2e.py
```

## Data model

- **Customer** — `id`, `name`, `email`, `phone` (optional)
- **Product** — `id`, `name`, `price`, `stock_quantity`
- **Order** — `id`, `customer_id`, `status` (`pending` / `flagged_for_review` / `fulfilled` / `negotiating` / `awaiting_response` / `updated` / `refunded` / `cancelled`)
- **OrderItem** — `order_id`, `product_id`, `quantity`
- **NegotiationOffer** — one per out-of-stock item in an order, tracks the original product, the alternative offered, and the customer's decision

## Key endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Redirects to `/dashboard` |
| `GET` | `/dashboard` | Live order-monitoring dashboard (static HTML/JS) |
| `GET` | `/health` | Plain health check |
| `POST` | `/orders` | Create a real order and kick off the triage graph. Validates that the customer and every product exist, and that quantities are positive. |
| `GET` | `/orders` | List all orders, including customer name (used by the dashboard table) |
| `GET` | `/orders/{id}` | Full order detail — items with product names/prices, and any negotiation offers with both the original and alternative product names |
| `GET` | `/respond?order_id=&decision=accept\|decline` | Resumes a paused negotiation. Called from the links inside the negotiation email. Validates `decision` is one of `accept`/`decline` and that the order exists. |
| `POST` | `/customers` | Create a customer (checks for duplicate email) |
| `GET` | `/products` | List all products with stock status — used to populate the demo product dropdown |
| `GET` | `/customers` | List all customers |
| `POST` | `/demo-order` | One-click demo endpoint — see below |

## The live demo flow

This is the feature a recruiter or reviewer actually uses to test the project without needing real data or backend access.

On the dashboard, clicking **"Try the live demo"** opens a modal where the visitor enters:
- **Name** and **email** (required) — used to find or create a `Customer` record
- **Phone** (optional)
- **Product** (optional, dropdown populated live from `GET /products`, showing each product's price and stock status) — if left on the default option, the order is placed against a product that's permanently kept out of stock in the seed data, guaranteeing the negotiation path triggers

On submit, `POST /demo-order`:
1. Finds or creates the customer
2. Places an order for the selected (or default) product
3. Runs the full LangGraph flow synchronously and returns the result

Two distinct paths a visitor can trigger depending on what they pick:
- **Out-of-stock product (default)** — triggers the full fraud check → inventory check → negotiation flow, and a real email arrives with working Accept/Decline links
- **In-stock product** — skips negotiation entirely; the order goes straight to `fulfilled` with no email, showing the "happy path"

## Running locally

1. Clone the repo and create a virtual environment.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in:
   - `DATABASE_URL` — a Postgres connection string (Neon free tier works well)
   - `BREVO_API_KEY` — from Brevo's **API keys & MCP** tab (starts with `xkeysib-`, *not* the SMTP tab's `xsmtpsib-` key — these are easy to confuse and only one works with the API client this project uses)
4. Run migrations: `alembic upgrade head`
5. Start the server: `uvicorn app.main:app --reload`
6. Open `http://127.0.0.1:8000/` — you'll land on the dashboard.

## Deployment

The frontend and backend deploy together as a single service — FastAPI serves the dashboard directly via a `StaticFiles` mount at `/dashboard`, so there's no separate hosting step for the UI.

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment variables:** `DATABASE_URL`, `BREVO_API_KEY`

> **Platform note:** this app depends on a LangGraph `PostgresSaver` checkpointer that opens a persistent database connection at startup and holds it open to support the real pause/resume negotiation flow. That needs a long-running process — a standard web service — not a stateless serverless function. Platforms with short function timeouts or per-request cold-start execution (e.g. Vercel's serverless functions) are a weaker fit for the `/respond` resume step; a host built for long-running processes (such as Render) is the safer choice for that part of the flow to behave reliably.

Also — the Accept/Decline links sent in negotiation emails are built from a base URL inside `app/services/email.py`. Whatever URL the app is actually reachable at, that file needs to point there, or the links in the email won't resolve for anyone testing from outside your own machine.

## Known limitations (intentionally deferred for this project's current scope)

- No authentication — all endpoints are open
- `/respond` doesn't verify the order was actually awaiting a response, so it can technically be called twice
- No timeout on stuck negotiations — an order can sit in `awaiting_response` indefinitely if a customer never clicks either link
- Customers are only created via `POST /customers`, `/demo-order`, or seed data — there's no signup flow
- SMS notifications are not yet implemented (email only)
- Negotiation is bundled per order (one email covering all out-of-stock items), not per individual item

## Tech stack

FastAPI · LangGraph · SQLAlchemy · Alembic · PostgreSQL (Neon) · Brevo (transactional email) · Vanilla HTML/CSS/JS dashboard