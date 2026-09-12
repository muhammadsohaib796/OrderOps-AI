from database import engine

try:
    with engine.connect() as conn:
        print("✅ Connected successfully!")
except Exception as e:
    print("❌ Connection failed:")
    print(e)