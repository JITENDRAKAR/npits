import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Instrument

symbols = ['JYOTIRES', 'SGBMAR31IV-GB', 'SHILCTECH']

print(f"{'Symbol':<20} | {'Found':<10} | {'Verified':<10} | {'Name'}")
print("-" * 60)

for symbol in symbols:
    inst = Instrument.objects.filter(symbol__iexact=symbol).first()
    if inst:
        print(f"{symbol:<20} | YES        | {inst.is_verified:<10} | {inst.name}")
    else:
        # Try partial match or alternate names
        print(f"{symbol:<20} | NO         | N/A        | N/A")
        
        # Search for similar symbols
        similar = Instrument.objects.filter(symbol__icontains=symbol[:4])[:3]
        if similar:
            print(f"  Similar symbols: {[s.symbol for s in similar]}")
