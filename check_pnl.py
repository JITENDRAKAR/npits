import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import PnLStatement, Instrument

def check_pnl(email):
    try:
        user = User.objects.get(email=email)
        inst = Instrument.objects.get(symbol='DLINKINDIA')
        pnls = PnLStatement.objects.filter(user=user, instrument=inst)
        
        print(f"PnL Records for {inst.symbol} ({user.email}):")
        for p in pnls:
            print(f"  {p.exit_date} | Qty: {p.quantity} | Buy: {p.buy_value} | Sell: {p.sell_value} | Profit: {p.realized_profit}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_pnl('jitendra.kar@gmail.com')
