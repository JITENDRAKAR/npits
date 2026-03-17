import os
import django
from datetime import date

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Transaction, Instrument

def check_today(email):
    try:
        user = User.objects.get(email=email)
        print(f"--- Transactions for {user.email} on 2026-03-10 ---")
        txs = Transaction.objects.filter(user=user, date=date(2026, 3, 10)).order_by('created_at')
        for tx in txs:
            print(f"  {tx.created_at} | {tx.transaction_type} | {tx.instrument.symbol} | Qty: {tx.quantity} | Rem: {getattr(tx, 'remaining_quantity', 0)} | Price: {tx.price}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_today('jitendra.kar@gmail.com')
