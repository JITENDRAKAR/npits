import os
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Portfolio, Transaction, Instrument

def fix_user_data(email, dry_run=True):
    try:
        user = User.objects.get(email=email)
        print(f"--- Processing {user.email} (Dry Run: {dry_run}) ---")
        
        # Get all distinct instruments this user has interacted with
        symbols = Transaction.objects.filter(user=user).values_list('instrument__symbol', flat=True).distinct()
        
        for symbol in symbols:
            inst = Instrument.objects.get(symbol=symbol)
            
            # Sum up all remaining quantities from BUY transactions
            lots = Transaction.objects.filter(
                user=user, 
                instrument=inst, 
                transaction_type='BUY', 
                remaining_quantity__gt=0
            )
            total_remaining = sum(l.remaining_quantity for l in lots)
            
            portfolio = Portfolio.objects.filter(user=user, instrument=inst).first()
            current_p_qty = portfolio.quantity if portfolio else 0
            
            if total_remaining != current_p_qty:
                print(f"Mismatch for {symbol}: Transaction Sum={total_remaining}, Portfolio={current_p_qty}")
                
                if not dry_run:
                    if total_remaining > 0:
                        # Calculate weighted average cost from remaining lots
                        total_cost = sum(Decimal(str(l.remaining_quantity)) * l.price for l in lots)
                        avg_cost = total_cost / Decimal(str(total_remaining))
                        
                        if portfolio:
                            portfolio.quantity = total_remaining
                            portfolio.avg_cost = avg_cost
                            portfolio.save()
                            print(f"  Updated Portfolio for {symbol}")
                        else:
                            # Restore deleted portfolio item
                            Portfolio.objects.create(
                                user=user,
                                instrument=inst,
                                quantity=total_remaining,
                                avg_cost=avg_cost,
                                ltp=inst.last_price or avg_cost
                            )
                            print(f"  Restored Portfolio for {symbol}")
                    elif total_remaining == 0 and portfolio:
                        portfolio.delete()
                        print(f"  Deleted empty Portfolio for {symbol}")

    except User.DoesNotExist:
        print(f"User with email {email} not found.")

if __name__ == "__main__":
    # First do a dry run
    fix_user_data('jitendra.kar@gmail.com', dry_run=True)
    # Then apply the fix
    print("\nApplying Fix...")
    fix_user_data('jitendra.kar@gmail.com', dry_run=False)
