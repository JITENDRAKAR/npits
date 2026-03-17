import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Transaction, Instrument

def debug_dlink(email):
    try:
        user = User.objects.get(email=email)
        inst = Instrument.objects.get(symbol='DLINKINDIA')
        txs = Transaction.objects.filter(user=user, instrument=inst).order_by('date', 'created_at')
        
        print(f"Transactions for {inst.symbol} ({user.email}):")
        total_remaining = 0
        for tx in txs:
            print(f"  {tx.date} | {tx.transaction_type} | Qty: {tx.quantity} | Rem: {getattr(tx, 'remaining_quantity', 'N/A')} | Price: {tx.price}")
            if tx.transaction_type == 'BUY':
                total_remaining += tx.remaining_quantity
        
        print(f"Total Remaining in Transaction Table: {total_remaining}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_dlink('jitendra.kar@gmail.com')
