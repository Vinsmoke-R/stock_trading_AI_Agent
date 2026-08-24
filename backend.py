from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))

# Database
db = client["stock_dataset"]   # databse
collection = db["user"]   # collection

trading_user = {
    "username": "trader_john",
    "account_type": "paper",  # or "live"
    "portfolio": {
        "cash": 10000.50,
        "buying_power": 40000,
        "portfolio_value": 50000.50,
        "positions": [
            {
                "symbol": "AAPL",
                "qty": 10,
                "avg_entry_price": 150.25,
                "current_price": 155.30,
                "unrealized_pl": 50.50
            },
            {
                "symbol": "GOOGL",
                "qty": 5,
                "avg_entry_price": 140.00,
                "current_price": 145.75,
                "unrealized_pl": 28.75
            }
        ]
    }
}

result = collection.insert_one(trading_user)
print(f"✅ Trading user created with ID: {result.inserted_id}")
print(f"✅ Database 'stock_dataset' created!")
print(f"✅ Collection 'user' created!")