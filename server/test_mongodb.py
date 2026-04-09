from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import os
from dotenv import load_dotenv

load_dotenv()

def test_mongodb_connection():
    """Test MongoDB Atlas connection"""
    mongodb_uri = os.environ.get('MONGODB_URI')
    
    if not mongodb_uri:
        print("❌ MONGODB_URI not found in .env file")
        return False
    
    try:
        # Connect to MongoDB
        client = MongoClient(mongodb_uri)
        
        # Ping the database
        client.admin.command('ping')
        
        print("✅ MongoDB Atlas connection successful!")
        print(f"   Server info: {client.server_info()['version']}")
        
        # Test database access
        db = client[os.environ.get('DATABASE_NAME', 'gesture_control')]
        collections = db.list_collection_names()
        print(f"   Database: {db.name}")
        print(f"   Collections: {collections if collections else 'None yet'}")
        
        return True
        
    except ConnectionFailure as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check if IP address is whitelisted in MongoDB Atlas")
        print("2. Verify username/password in connection string")
        print("3. Ensure network allows outbound connections to port 27017")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("Testing MongoDB Atlas Connection")
    print("=" * 50)
    test_mongodb_connection()