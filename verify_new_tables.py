import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Instrument, Watchlist, Dividend, InvestmentGoal
from datetime import date

def verify():
    print("Verifying new tables...")
    
    # Get or create a test user
    user, _ = User.objects.get_or_create(username='test_verify_user')
    
    # Get or create a test instrument
    instrument, _ = Instrument.objects.get_or_create(symbol='RELIANCE', defaults={'name': 'Reliance Industries'})
    
    try:
        # Test Watchlist
        w, created = Watchlist.objects.get_or_create(user=user, instrument=instrument, defaults={'notes': 'Testing watchlist'})
        print(f"Watchlist: {'Created' if created else 'Exists'} - OK")
        
        # Test Dividend
        d = Dividend.objects.create(user=user, instrument=instrument, amount=10.5, received_date=date.today())
        print(f"Dividend: Created - OK")
        
        # Test InvestmentGoal
        g = InvestmentGoal.objects.create(user=user, name='Retirement', target_amount=1000000, target_date=date(2040, 1, 1))
        print(f"InvestmentGoal: Created - OK")
        
        # Clean up
        d.delete()
        g.delete()
        if created:
            w.delete()
        
        print("\nAll new tables verified successfully!")
        
    except Exception as e:
        print(f"Verification FAILED: {e}")

if __name__ == "__main__":
    verify()
