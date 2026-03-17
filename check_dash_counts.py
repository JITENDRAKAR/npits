import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.utils import get_recommendations

User = get_user_model()
try:
    user = User.objects.get(email='jitendra.kar@gmail.com')
    recommendations, realized_profits, _ = get_recommendations(user)
    
    # Dashboard view filtering logic
    dash_recommendations = [
        r for r in recommendations 
        if r.get('in_portfolio', False) or (r.get('action') == 'BUY' and r.get('realized_profit', 0) > 0)
    ]
    
    buy_recommendations = [r for r in dash_recommendations if r['action'] == 'BUY']
    sell_recommendations = [r for r in dash_recommendations if r['action'] == 'SELL']
    reduce_sigs = [r for r in dash_recommendations if r['action'] == 'REDUCE']
    
    print(f"Dashboard Buy signals length: {len(buy_recommendations)}")
    print(f"Dashboard Sell signals length: {len(sell_recommendations)}")
    print(f"Dashboard Reduce signals length: {len(reduce_sigs)}")
    print(f"Total shown in dropdowns: {len(buy_recommendations) + len(sell_recommendations) + len(reduce_sigs)}")

    # Context processor logic
    user_signals = [r for r in recommendations if r.get('in_portfolio', False)]
    buy_count = sum(1 for r in user_signals if r.get('action') == 'BUY')
    reduce_count = sum(1 for r in user_signals if r.get('action') == 'REDUCE')
    sell_count = sum(1 for r in user_signals if r.get('action') == 'SELL')
    
    print(f"Context Processor Total: {buy_count + reduce_count + sell_count}")
    print(f"Context Processor Buy: {buy_count}")
    print(f"Context Processor Reduce: {reduce_count}")
    print(f"Context Processor Sell: {sell_count}")

except Exception as e:
    print(f"Error: {e}")
