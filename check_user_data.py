import os
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Portfolio, Transaction, Instrument

def check_user_data(email):
    try:
        user = User.objects.get(email=email)
        print(f"User: {user.username} ({user.email})")
        
        # Check Transaction vs Portfolio for all instruments
        symbols = Transaction.objects.filter(user=user).values_list('instrument__symbol', flat=True).distinct()
        
        for symbol in symbols:
            inst = Instrument.objects.get(symbol=symbol)
            portfolio = Portfolio.objects.filter(user=user, instrument=inst).first()
            p_qty = portfolio.quantity if portfolio else 0
            
            t_qty = sum(t.remaining_quantity for t in Transaction.objects.filter(
                user=user, instrument=inst, transaction_type='BUY', remaining_quantity__gt=0
            ))
            
            if p_qty != t_qty:
                print(f"MISMATCH found for {symbol}:")
                print(f"  Portfolio Quantity: {p_qty}")
                print(f"  Sum of Transaction Lots: {t_qty}")
                if p_qty == 0 and t_qty > 0:
                    print(f"  ACTION: Should restore Portfolio item for {symbol}")
            else:
                if p_qty > 0:
                    print(f"  {symbol}: {p_qty} (OK)")

    except User.DoesNotExist:
        print(f"User with email {email} not found.")

if __name__ == "__main__":
    check_user_data('jitendra.kar@gmail.com')
