import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

# Load variables from .env into the environment
load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    raise RuntimeError(
        "Missing APCA_API_KEY_ID or APCA_API_SECRET_KEY.\n"
        "Copy .env.example to .env and fill in your real Alpaca paper trading keys."
    )

# paper=True points this at Alpaca's paper trading environment
# (equivalent to hitting https://paper-api.alpaca.markets under the hood)
client = TradingClient(API_KEY, SECRET_KEY, paper=True)

def main():
    account = client.get_account()

    print("Connected to Alpaca paper trading account.\n")
    print(f"Account status:     {account.status}")
    print(f"Cash:                ${account.cash}")
    print(f"Equity:              ${account.equity}")
    print(f"Buying power:        ${account.buying_power}")
    print(f"Portfolio value:     ${account.portfolio_value}")
    print(f"Pattern day trader:  {account.pattern_day_trader}")

    # List current open positions (will be empty on a fresh account)
    positions = client.get_all_positions()
    if positions:
        print(f"\nOpen positions ({len(positions)}):")
        for p in positions:
            print(f"  {p.symbol}: {p.qty} shares @ avg ${p.avg_entry_price}")
    else:
        print("\nNo open positions yet (expected for a fresh paper account).")

if __name__ == "__main__":
    main()