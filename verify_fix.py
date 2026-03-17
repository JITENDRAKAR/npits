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

    print(f"--- Starting Verification after Fix ---")
    
    # 2. Simulate Multi-lot Upload with FIX
    lots = [
        {'Instrument': 'AARTIPHARM_REPRO', 'Quantity': 5, 'Average Cost': 100.0, 'LTP': 100.0},
        {'Instrument': 'AARTIPHARM_REPRO', 'Quantity': 1, 'Average Cost': 110.0, 'LTP': 100.0},
    ]
    
    # Mirrored logic from NEW upload_portfolio (views.py)
    aggregated_data = {}
    for row in lots:
        symbol = row['Instrument']
        qty = row['Quantity']
        avg = row['Average Cost']
        ltp = row['LTP']

        Transaction.objects.create(
            user=user,
            instrument=inst,
            transaction_type='BUY',
            quantity=qty,
            remaining_quantity=qty,
            price=avg,
            date=timezone.now().date()
        )

        if symbol not in aggregated_data:
            aggregated_data[symbol] = {
                'qty': qty,
                'total_cost': Decimal(str(qty)) * Decimal(str(avg)),
                'ltp': ltp,
                'instrument': inst
            }
        else:
            aggregated_data[symbol]['qty'] += qty
            aggregated_data[symbol]['total_cost'] += Decimal(str(qty)) * Decimal(str(avg))
            if ltp > 0: aggregated_data[symbol]['ltp'] = ltp

    for symbol, data in aggregated_data.items():
        qty = data['qty']
        avg_cost = data['total_cost'] / Decimal(str(qty))
        portfolio, _ = Portfolio.objects.get_or_create(
            user=user, instrument=inst,
            defaults={'quantity': qty, 'avg_cost': avg_cost, 'ltp': data['ltp']}
        )
        portfolio.quantity = qty
        portfolio.avg_cost = avg_cost
        portfolio.save()

    # Verify State after Upload
    portfolio = Portfolio.objects.get(user=user, instrument=inst)
    print(f"Portfolio Quantity (Expected 6): {portfolio.quantity}")
    
    # 3. Simulate Sell of 1 Unit
    quantity_to_sell = 1
    price = Decimal('120.0')
    
    portfolio.quantity -= quantity_to_sell
    
    if portfolio.quantity == 0:
        print("BUG TRIGGERED: Portfolio quantity reached 0 after selling 1 unit. FAIL.")
        portfolio.delete()
    else:
        portfolio.save()
        print(f"Portfolio still exists. Current qty: {portfolio.quantity}")

    # Final Check
    portfolio_exists = Portfolio.objects.filter(user=user, instrument=inst).exists()
    if portfolio_exists and portfolio.quantity == 5:
        print("SUCCESS: Portfolio still exists with remaining qty: 5")
    else:
        print(f"VERIFICATION FAILED. Exists: {portfolio_exists}, Qty: {portfolio.quantity if portfolio_exists else 'N/A'}")

if __name__ == "__main__":
    reproduce()
