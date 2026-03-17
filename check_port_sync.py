import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Transaction, Portfolio, Instrument
from django.contrib.auth import get_user_model
from django.db.models import Sum

User = get_user_model()
user = User.objects.get(email='jitendra.kar@gmail.com')

print(f"--- Checking Portfolio vs Transactions for {user.username} (ID: {user.id}) ---")

portfolios = Portfolio.objects.filter(user=user).select_related('instrument')
print(f"{'Symbol':<15} | {'Port Qty':<10} | {'Sum Tx Qty':<10} | {'Missing Tx?'}")
print("-" * 50)

for p in portfolios:
    tx_sum = Transaction.objects.filter(
        user=user, 
        instrument=p.instrument, 
        transaction_type='BUY'
    ).aggregate(total=Sum('remaining_quantity'))['total'] or 0
    
    missing = "YES" if tx_sum == 0 and p.quantity > 0 else "No"
    print(f"{p.instrument.symbol:<15} | {p.quantity:<10} | {tx_sum:<10} | {missing}")

# Check for symbols with Transactions but no Portfolio
tx_symbols = Transaction.objects.filter(user=user).values_list('instrument__symbol', flat=True).distinct()
port_symbols = [p.instrument.symbol for p in portfolios]
orphans = [s for s in tx_symbols if s not in port_symbols]
if orphans:
    print("\nSymbols with Transactions but no Portfolio (Orphans):")
    for s in orphans:
        print(f"  {s}")
