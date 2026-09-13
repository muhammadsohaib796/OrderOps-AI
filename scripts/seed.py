from app.database import SessionLocal
from app.models import Customer, Product, Order, OrderItem, OrderStatus

db = SessionLocal()

try:
    existing = db.query(Customer).filter(Customer.email == "alice@example.com").first()
    if existing:
        print("Seed data already exists — skipping. Run the cleanup script first if you want to reseed.")
    else:
        #Customer
        alice = Customer(name="Alice Khan", email="alice@example.com", phone="03001234567")
        bilal = Customer(name="Bilal Ahmed", email="bilal@example.com", phone=None)


        # Products — note the second one is intentionally out of stock
        mug = Product(name="Ceramic Mug", price=8.99, stock_quantity=50)
        hoodie = Product(name="Limited Edition Hoodie", price=45.00, stock_quantity=0)
        hoodie_alt = Product(name="Standard Hoodie", price=40.00, stock_quantity=30)

        db.add_all([alice, bilal, mug, hoodie, hoodie_alt])
        db.commit()  # commit here so alice/hoodie/etc. get real IDs before we reference them

        # Refresh to load the auto-generated IDs
        db.refresh(alice)
        db.refresh(hoodie)

        # An order for the out-of-stock hoodie — this is the case that should trigger negotiation
        order = Order(customer_id=alice.id, status=OrderStatus.pending)
        db.add(order)
        db.commit()
        db.refresh(order)

        order_item = OrderItem(order_id=order.id, product_id=hoodie.id, quantity=1)
        db.add(order_item)
        db.commit()

        print(f"Seeded successfully. Test order ID: {order.id} (Alice, out-of-stock hoodie)")

except Exception as e:
    db.rollback()
    print("Seeding failed:", e)

finally:
    db.close()