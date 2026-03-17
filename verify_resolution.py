import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.utils import resolve_instrument

test_cases = [
    'JYOTIRES',         # Should match name JYOTIRES (Symbol BOM:514448)
    'SHILCTECH',        # Should match name SHILCTECH (Symbol BOM:531201)
    'SGBMAR31IV-GB',    # Should match symbol SGBMAR31IV
    'RELIANCE',         # Exact symbol match
    'NONEXISTENT'       # Should return None
]

print(f"{'Input':<20} | {'Found Symbol':<15} | {'Verified'}")
print("-" * 50)

for tc in test_cases:
    inst = resolve_instrument(tc)
    if inst:
        print(f"{tc:<20} | {inst.symbol:<15} | {inst.is_verified}")
    else:
        print(f"{tc:<20} | {'NOT FOUND':<15} | N/A")
