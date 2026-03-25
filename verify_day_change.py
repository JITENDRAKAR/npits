import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.utils import perform_sync
from core.models import Instrument

print("Starting sync...")
perform_sync()
print("Sync complete.")

print("\nVerifying Instrument Data:")
instruments = Instrument.objects.filter(last_price__gt=0).order_by('-last_updated')[:5]
for inst in instruments:
    print(f"Symbol: {inst.symbol}")
    print(f"  LTP: {inst.last_price}")
    print(f"  Change: {inst.price_change}")
    print(f"  Prev Close: {inst.previous_close}")
    expected_prev = inst.last_price - inst.price_change
    print(f"  Calculation check: {inst.last_price} - {inst.price_change} = {expected_prev}")
    print(f"  Match? {inst.previous_close == expected_prev}")
    print("-" * 20)
