import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Transaction, Instrument, Portfolio

def comprehensive_debug(email):
    try:
        user = User.objects.get(email=email)
        print(f"--- Comprehensive Debug for {user.email} ---")
        
        print("\nCurrent Portfolio:")
        for p in Portfolio.objects.filter(user=user):
            print(f"  {p.instrument.symbol} | Qty: {p.quantity} | Avg: {p.avg_cost}")
            
        print("\nAll Transactions (last 20):")
        txs = Transaction.objects.filter(user=user).order_by('-date', '-created_at')[:20]
        for tx in txs:
            print(f"  {tx.date} | {tx.transaction_type} | {tx.instrument.symbol} | Qty: {tx.quantity} | Rem: {getattr(tx, 'remaining_quantity', 0)} | Price: {tx.price}")

        # Search for any BUY transactions for anything like DLINK
        print("\nSearching for DLINK related buys:")
        dlink_buys = Transaction.objects.filter(
            user=user, 
            instrument__symbol__icontains='DLINK', 
            transaction_type='BUY'
        )
        if not dlink_buys.exists():
            print("  No DLINK buys found.")
        for tx in dlink_buys:
            print(f"  {tx.date} | {tx.instrument.symbol} | Qty: {tx.quantity} | Rem: {tx.remaining_quantity}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    comprehensive_debug('jitendra.kar@gmail.com')
