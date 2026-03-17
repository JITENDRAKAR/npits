import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Instrument

codes = ['BOM:514448', 'BOM:531201', 'SGBMAR31IV']

for s in codes:
    inst = Instrument.objects.filter(symbol__iexact=s).first()
    print(f"{s}: Found={bool(inst)}, Verified={inst.is_verified if inst else None}, Name={inst.name if inst else None}")
