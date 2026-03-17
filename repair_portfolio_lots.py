import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Transaction, Portfolio, Instrument
from django.contrib.auth import get_user_model
from django.db.models import Sum

User = get_user_model()

print("--- Starting Portfolio Lot Repair ---")

all_portfolios = Portfolio.objects.all().select_related('user', 'instrument')
repaired_count = 0

for p in all_portfolios:
    # Calculate sum of remaining quantities in BUY transactions
    tx_sum = Transaction.objects.filter(
        user=p.user, 
        instrument=p.instrument, 
        transaction_type='BUY'
    ).aggregate(total=Sum('remaining_quantity'))['total'] or 0
    
    diff = p.quantity - tx_sum
    
    if diff > 0:
        print(f"Repairing {p.instrument.symbol} for {p.user.username}: adding {diff} units to transactions.")
        # Create a placeholder BUY transaction for the missing units
        Transaction.objects.create(
            user=p.user,
            instrument=p.instrument,
            transaction_type='BUY',
            quantity=diff,
            remaining_quantity=diff,
            price=p.avg_cost,
            date=p.user.date_joined.date()  # Use user join date as a fallback for legacy data
        )
        repaired_count += 1

print(f"--- Repair Complete. {repaired_count} portfolio items repaired. ---")
