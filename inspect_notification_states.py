import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import SignalNotificationState
from django.contrib.auth.models import User

print(f"{'User':<30} | {'Buy':<5} | {'Red':<5} | {'Sel':<5} | {'Last Notified'}")
print("-" * 80)

for state in SignalNotificationState.objects.all():
    print(f"{state.user.email:<30} | {state.last_buy_count:<5} | {state.last_reduce_count:<5} | {state.last_sell_count:<5} | {state.last_notified_at}")
