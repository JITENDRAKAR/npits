import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Transaction, Portfolio, Instrument, PnLStatement
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(email='jitendra.kar@gmail.com')
inst = Instrument.objects.get(symbol='LIQUIDCASE')

original_total_qty = 1672
original_total_value = Decimal('188509.48')
sold_qty = 770
remaining_qty = original_total_qty - sold_qty # 902
avg_cost = original_total_value / Decimal(str(original_total_qty))

print(f"Restoring LIQUIDCASE for {user.email}")
print(f"  Avg Cost: {avg_cost}")
print(f"  Remaining Qty: {remaining_qty}")

# 1. Create/Update Transactions
# Delete the erroneous SELL record's logic (which had 0 buy value) if needed? 
# Actually, I'll just fix the PnLStatement and Transactions.

# Create BUY for the full 1672? Or split it. 
# Better to create one lot for the remaining 902 and one (zeroed) lot for the 770.

# Clear existing LIQUIDCASE transactions for this user to start clean?
Transaction.objects.filter(user=user, instrument=inst).delete()

# Create Lot for the 902 remaining
Transaction.objects.create(
    user=user,
    instrument=inst,
    transaction_type='BUY',
    quantity=original_total_qty, # Total history
    remaining_quantity=remaining_qty,
    price=avg_cost,
    date=user.date_joined.date()
)

# Create Sell Transaction (already exists in the real world but let's re-record it)
sell_price = Decimal('113.14')
from datetime import date
Transaction.objects.create(
    user=user,
    instrument=inst,
    transaction_type='SELL',
    quantity=sold_qty,
    price=sell_price,
    date=date(2026, 3, 13)
)

# 2. Fix PnLStatement
pnl = PnLStatement.objects.filter(user=user, instrument=inst, quantity=sold_qty).first()
if pnl:
    pnl.buy_value = Decimal(str(sold_qty)) * avg_cost
    pnl.sell_value = Decimal(str(sold_qty)) * sell_price
    pnl.realized_profit = pnl.sell_value - pnl.buy_value
    pnl.save()
    print(f"  Updated PnLStatement ID {pnl.id}: Profit={pnl.realized_profit}")

# 3. Restore Portfolio
Portfolio.objects.update_or_create(
    user=user,
    instrument=inst,
    defaults={
        'quantity': remaining_qty,
        'avg_cost': avg_cost,
        'ltp': inst.last_price or avg_cost
    }
)

print("--- LIQUIDCASE Restored Successfully ---")
