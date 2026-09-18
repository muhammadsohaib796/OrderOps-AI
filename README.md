# 🤖 OrderOps AI

## 🚀 Autonomous Order Triage & Resolution Agent

OrderOps AI is an AI powered order recovery system that helps recover potentially lost e commerce sales when an ordered product is out of stock.

The system automatically processes orders, checks fraud risk and inventory, finds an available alternative product, creates a negotiation offer, and sends the customer an email with accept or decline options.

The workflow is orchestrated with LangGraph and can pause while waiting for the customer's response, then resume later and update the order accordingly.

Built as a learning and portfolio project based on a Business Requirements Document, focusing on LangGraph stateful workflows, FastAPI, PostgreSQL, and transactional email integration.

## ✨ What It Does

### 📦 1. Order Intake

A customer order is submitted through the FastAPI backend.

The system creates the order and its items in PostgreSQL before starting the processing workflow.

### 🛡️ 2. Fraud Risk Check

Each order receives a rule based risk score based on factors such as:

• 💰 Order value

• 📞 Missing customer contact information

• 📦 Unusually large item quantities

High risk orders can be flagged for review instead of being automatically processed.

### 📊 3. Inventory Validation

The system checks the stock quantity of products included in the order.

If all products are available, the order can proceed toward fulfillment without negotiation.

### 🔄 4. Alternative Product Discovery

If a product is out of stock, the system searches available products for a similar in stock alternative.

The alternative product is then used to create a negotiation offer.

### 💬 5. Customer Negotiation

The system creates a negotiation offer with a discount and sends the customer an email through Brevo.

The email contains options for the customer to accept or decline the proposed alternative.

### ⏸️ 6. Stateful Pause & Resume

When customer input is required, the LangGraph workflow pauses.

The graph state is persisted using a PostgreSQL checkpointer.

When the customer responds, the application resumes the existing workflow using the order ID as the LangGraph thread ID.

The order can then be updated or refunded depending on the customer's decision.

## 🏗️ Architecture

```text
👤 Customer Order
        │
        ▼
    ⚡ FastAPI
        │
        ▼
   🧠 LangGraph
        │
        ├── 🛡️ Fraud Check
        │
        ├── 📦 Inventory Check
        │
        ├── 🔎 Find Alternative
        │
        ├── 📝 Create Negotiation Offer
        │
        ├── 📧 Send Customer Email
        │
        └── ⏸️ Await Customer Response
                    │
                    ▼
          👤 Customer Accepts / Declines
                    │
                    ▼
            🔄 Resume LangGraph
                    │
                    ▼
              💾 Update Order


### 🛠️ Tech Stack 
| Technology                 | Purpose                         |
| -------------------------- | ------------------------------- |
| 🐍 Python                  | Core programming language       |
| ⚡ FastAPI                  | Backend API                     |
| 🧠 LangGraph               | Stateful workflow orchestration |
| 🗄️ PostgreSQL             | Application database            |
| ☁️ Neon                    | PostgreSQL hosting              |
| 🔗 SQLAlchemy              | ORM and database operations     |
| 🔄 Alembic                 | Database migrations             |
| ✅ Pydantic                 | Request validation              |
| 📧 Brevo                   | Transactional email             |
| 🌐 HTML / CSS / JavaScript | Operations dashboard            |


### 📁 Project Structure
app/
├── main.py
├── database.py
├── models.py
├── schemas.py
│
├── graph/
│   ├── state.py
│   └── graph.py
│
├── services/
│   └── email.py
│
└── static/
    └── index.html

alembic/
    Database migrations

scripts/
├── seed.py
├── test_graph.py
└── test_e2e.py

.env.example
requirements.txt
README.md


###🔌 API Endpoints

| Method  | Endpoint     | Purpose                         |
| ------- | ------------ | ------------------------------- |
| 📥 POST | `/orders`    | Create and process an order     |
| 📋 GET  | `/orders`    | List existing orders            |
| 💬 GET  | `/respond`   | Accept or decline a negotiation |
| 📊 GET  | `/dashboard` | Open the operations dashboard   |
| 📚 GET  | `/docs`      | Open FastAPI documentation      |


🚀 Running Locally
1️⃣ Clone the repository
git clone <your repository URL>
cd OrderOps AI

2️⃣ Create a virtual environment
Windows:
python -m venv venv
venv\Scripts\activate

3️⃣ Install dependencies
pip install -r requirements.txt
4️⃣ Configure environment variables

Create a .env file based on .env.example.

Example:

DATABASE_URL=your_postgresql_connection_string

BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=your_verified_sender_email
BREVO_SENDER_NAME=OrderOps AI

⚠️ Never commit your .env file or API keys to GitHub.

5️⃣ Run database migrations
alembic upgrade head
6️⃣ Seed sample data
python -m scripts.seed
7️⃣ Start the FastAPI server
uvicorn app.main:app --reload

Then open:

📚 API Documentation

http://127.0.0.1:8000/docs

📊 Operations Dashboard

http://127.0.0.1:8000/dashboard
🎯 Live Demo

The dashboard includes a Try Live Demo option.

The demo creates a test order containing an intentionally unavailable product and starts the complete recovery workflow.

📦 Create Order
       ↓
🛡️ Fraud Check
       ↓
📊 Inventory Check
       ↓
⚠️ Detect Out of Stock
       ↓
🔎 Find Alternative
       ↓
📝 Create Offer
       ↓
📧 Send Email
       ↓
⏸️ Wait for Customer
       ↓
✅ Accept / ❌ Decline
       ↓
🔄 Resume Workflow
       ↓
💾 Update Order

⚠️ Note: The demo sends a real transactional email to the email address entered during testing.
🧪 Testing

Run the end to end tests with:

python scripts/test_e2e.py
✅ Happy Path

An in stock product is ordered and the system processes it without negotiation.

🔄 Negotiation Path

An out of stock product is ordered, an alternative is found, the workflow pauses, and the customer response resumes the workflow.

🧠 LangGraph Workflow

The workflow uses a StateGraph to coordinate the order processing process.

The graph maintains state such as:

order_id
customer_id
risk_score
is_flagged
out_of_stock_items
alternative_product_id
customer_response
final_status

The order ID is also used as the LangGraph thread_id, allowing the application to resume the correct workflow when the customer responds later.

🗄️ Database

PostgreSQL is used for application data and LangGraph checkpoint persistence.

The application uses:

• 🔗 SQLAlchemy ORM for database operations

• 🔄 Alembic for database migrations

• ☁️ Neon PostgreSQL for cloud database hosting

Main entities include:

👤 Customer
📦 Product
🛒 Order
📋 OrderItem
💬 NegotiationOffer
📧 Email Integration

OrderOps AI uses Brevo for transactional email delivery.

The application sends negotiation emails containing the proposed alternative product and customer response options.

For local development, a verified sender email can be used without purchasing a custom domain.

⚠️ Known Limitations

This is a learning and portfolio project and is not intended to be used as a production e commerce system.

Current limitations include:

• 🔐 No authentication or authorization
• 🔗 Customer response links are not protected by authentication or secure tokens
• ⚠️ /respond does not currently verify that an order is actually waiting for a customer response
• ⏱️ There is no timeout for negotiations that receive no response
• 📱 SMS negotiation from the original requirements is not implemented
• 🛡️ Fraud detection is rule based rather than a trained fraud detection model
• 🔎 Alternative product selection uses a simple similarity approach

🔮 Future Improvements

Potential future improvements include:

• 🔐 Authentication and role based access control

• 🔑 Secure customer response tokens

• ⏱️ Negotiation expiration and timeout handling

• 📱 SMS notifications

• 🧠 More advanced product similarity matching

• 🛡️ Improved fraud detection

• 📧 Better customer communication templates

• 🚀 Production deployment

• 📊 Monitoring and logging

🎓 Project Goals

This project was built to gain practical experience with:

• 🧠 LangGraph stateful workflows
• 🔀 Conditional graph routing
• 👤 Customer in the loop workflows
• 💾 PostgreSQL checkpoint persistence
• ⚡ FastAPI backend development
• 🔗 SQLAlchemy database integration
• 🔄 Alembic migrations
• 📧 Transactional email APIs
• 🧪 End to end API testing
• 📋 Building an AI enabled backend system from a Business Requirements Document

📜 License

This project is intended for educational and portfolio purposes.













