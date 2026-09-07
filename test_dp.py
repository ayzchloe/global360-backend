from database import engine, Base # Adjust based on your database module name
from sqlalchemy import text

def test_connection():
    try:
        # Check connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database connection successful!")

        # Create missing tables if they don't exist
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified successfully!")

    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    test_connection()