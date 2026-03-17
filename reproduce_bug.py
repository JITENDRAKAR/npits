import os
import django
import pandas as pd
from decimal import Decimal
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Portfolio, Transaction, Instrument, PnLStatement

def reproduce():
    # 1. Setup - Create a test user and instrument
    user, _ = User.objects.get_or_create(username='testuser_bug_repo')
    user.set_password('password123')
    user.save()
    
    inst, _ = Instrument.objects.get_or_create(
        symbol='AARTIPHARM_REPRO', 
        defaults={'name': 'Aarti Pharm Repro', 'is_verified': True}
    )
    
    # Cleanup any existing data for this test case
    Portfolio.objects.filter(user=user, instrument=inst).delete()
    Transaction.objects.filter(user=user, instrument=inst).delete()
    PnLStatement.objects.filter(user=user, instrument=inst).delete()

    print(f"--- Starting Reproduction ---")
    
    # 2. Simulate Multi-lot Upload
    # Imagine a CSV with 2 lots of AARTIPHARM
    lots = [
        {'Instrument': 'AARTIPHARM_REPRO', 'Quantity': 5, 'Average Cost': 100.0, 'LTP': 100.0},
        {'Instrument': 'AARTIPHARM_REPRO', 'Quantity': 1, 'Average Cost': 110.0, 'LTP': 100.0},
    ]
    
    for row in lots:
        symbol = row['Instrument']
        qty = row['Quantity']
        avg = row['Average Cost']
        
        # This mirrors the logic in upload_portfolio (views.py)
        Transaction.objects.create(
            user=user,
            instrument=inst,
            transaction_type='BUY',
            quantity=qty,
            remaining_quantity=qty,
            price=avg,
            date=timezone.now().date()
        )

        portfolio, created = Portfolio.objects.get_or_create(
            user=user,
            instrument=inst,
            defaults={'quantity': qty, 'avg_cost': avg, 'ltp': 100.0}
        )
        if not created:
            portfolio.quantity = qty  # BUG: This overwrites instead of adding
            portfolio.avg_cost = avg
            portfolio.save()
            
    # Verify State after Upload
    portfolio = Portfolio.objects.get(user=user, instrument=inst)
    print(f"Portfolio Quantity (Expected 6, Bot 1?): {portfolio.quantity}")
    
    # 3. Simulate Sell of 1 Unit
    # This mirrors sell_stock (views.py)
    quantity_to_sell = 1
    price = Decimal('120.0')
    
    original_qty = portfolio.quantity
    portfolio.quantity -= quantity_to_sell
    
    if portfolio.quantity == 0:
        print("BUG TRIGGERED: Portfolio quantity reached 0 after selling 1 unit (because it was incorrectly set to 1 instead of 6). Deleting portfolio item.")
        portfolio.delete()
    else:
        # Recalculate average cost (this logic is in sell_stock too)
        remaining_lots = Transaction.objects.filter(
            user=user,
            instrument=inst,
            transaction_type='BUY',
            remaining_quantity__gt=0
        )
        total_qty = sum(l.remaining_quantity for l in remaining_lots)
        print(f"Remaining quantity in Transaction table: {total_qty}")
        # Note: In the real code, it doesn't update portfolio.quantity here, 
        # it just updates avg_cost and saves.
        portfolio.save()

    # Final Check
    portfolio_exists = Portfolio.objects.filter(user=user, instrument=inst).exists()
    if not portfolio_exists and original_qty == 1:
        print("FAIL: Portfolio item was deleted because it thought only 1 unit was held.")
    elif portfolio_exists:
        print(f"SUCCESS: Portfolio still exists. Remaining qty: {Portfolio.objects.get(user=user, instrument=inst).quantity}")
    else:
        print("Portfolio deleted.")

if __name__ == "__main__":
    reproduce()
