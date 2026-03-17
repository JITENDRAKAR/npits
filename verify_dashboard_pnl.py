
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.views import dashboard
from django.test import RequestFactory
from django.contrib.auth.models import User

def verify_dashboard_context():
    factory = RequestFactory()
    user = User.objects.first()
    if not user:
        print("No user found in database. Skipping verification.")
        return

    request = factory.get('/dashboard/')
    request.user = user
    
    # We need to mock the context if we can't run the actual view due to complex dependencies
    # But let's try calling it and see if it works
    try:
        response = dashboard(request)
        context = response.context_data if hasattr(response, 'context_data') else getattr(response, 'context', {})
        
        total_invested = context.get('total_invested', 0)
        total_unrealized_pnl = context.get('total_unrealized_pnl', 0)
        total_unrealized_pnl_percent = context.get('total_unrealized_pnl_percent', 0)
        
        print(f"Total Invested: {total_invested}")
        print(f"Total Unrealized P&L: {total_unrealized_pnl}")
        print(f"Total Unrealized P&L %: {total_unrealized_pnl_percent}")
        
        if total_invested > 0:
            expected_percent = (total_unrealized_pnl / total_invested) * 100
            if abs(total_unrealized_pnl_percent - expected_percent) < 0.01:
                print("Verification SUCCESS: Percentage calculation is correct.")
            else:
                print(f"Verification FAILURE: Expected {expected_percent}, got {total_unrealized_pnl_percent}")
        else:
            print("Total invested is 0, percentage should be 0.")
            if total_unrealized_pnl_percent == 0:
                print("Verification SUCCESS.")
            else:
                print(f"Verification FAILURE: Expected 0, got {total_unrealized_pnl_percent}")
                
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    verify_dashboard_context()
