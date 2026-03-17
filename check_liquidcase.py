import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Transaction, Portfolio, Instrument, PnLStatement
from django.contrib.auth import get_user_model

User = get_user_model()

symbol = 'LIQUIDCASE'
print(f"--- Checking for symbol: {symbol} ---")

# Find instruments matching the symbol
instruments = Instrument.objects.filter(symbol__iexact=symbol)
for inst in instruments:
    print(f"Instrument: {inst.id}, Symbol: {inst.symbol}, Verified: {inst.is_verified}")

    # For each instrument, find related transactions
    txs = Transaction.objects.filter(instrument=inst).order_by('date', 'created_at')
    print(f"\nTransactions for {inst.symbol}:")
    for tx in txs:
        print(f"  ID: {tx.id}, User: {tx.user.username}, Type: {tx.transaction_type}, Qty: {tx.quantity}, Rem: {tx.remaining_quantity if hasattr(tx, 'remaining_quantity') else 'N/A'}, Price: {tx.price}, Date: {tx.date}")

    # Check portfolio state
    ports = Portfolio.objects.filter(instrument=inst)
    print(f"\nPortfolio Records for {inst.symbol}:")
    for p in ports:
        print(f"  ID: {p.id}, User: {p.user.username}, Qty: {p.quantity}, AvgCost: {p.avg_cost}")

    # Check PnLStatement
    pnls = PnLStatement.objects.filter(instrument=inst)
    print(f"\nPnL Statements for {inst.symbol}:")
    for p in pnls:
        print(f"  ID: {p.id}, User: {p.user.username}, Qty: {p.quantity}, BuyVal: {p.buy_value}, SellVal: {p.sell_value}, Profit: {p.realized_profit}")
