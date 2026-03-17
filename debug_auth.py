import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from core.models import Profile

email = 'jitendra.kar@gmail.com'
mobile = '9871808718'
password = 'anirudha'

print(f"--- Debugging for {email} / {mobile} ---")

# 1. Check if user exists by email
try:
    user = User.objects.get(email__iexact=email)
    print(f"User found by email: {user.username} (ID: {user.id})")
    
    print(f"User has usable password: {user.has_usable_password()}")
    print(f"Direct check_password('anirudha'): {user.check_password('anirudha')}")
    
    # Check Auth for another candidate
    print("\n--- Testing jitendrakar candidate ---")
    res_jitendrakar = authenticate(username='jitendrakar', password=password)
    print(f"Authenticate 'jitendrakar' with 'anirudha': {'SUCCESS' if res_jitendrakar else 'FAILED'}")

    res_winmedicare = authenticate(username='jitendra.kar@winmedicare.com', password=password)
    print(f"Authenticate 'jitendra.kar@winmedicare.com' with 'anirudha': {'SUCCESS' if res_winmedicare else 'FAILED'}")

    # Check Auth
    res_email = authenticate(username=email, password=password)
    print(f"Authenticate with email: {'SUCCESS' if res_email else 'FAILED'}")
    
    res_mobile = authenticate(username=mobile, password=password)
    print(f"Authenticate with mobile: {'SUCCESS' if res_mobile else 'FAILED'}")

except User.DoesNotExist:
    print(f"User with email {email} NOT found.")

# 2. Check if any user has this mobile number
profiles = Profile.objects.filter(mobile_number=mobile)
if profiles.exists():
    for p in profiles:
        print(f"Found profile with mobile {mobile}: user {p.user.username} (email: {p.user.email})")
else:
    print(f"No profile found with mobile number {mobile}.")

# 4. Check Social Accounts
from allauth.socialaccount.models import SocialAccount
social_accounts = SocialAccount.objects.filter(user=user)
if social_accounts.exists():
    for sa in social_accounts:
        print(f"User is linked to social provider: {sa.provider} (UID: {sa.uid})")
else:
    print("User is NOT linked to any social account.")

# 5. List all users and test password
print("\n--- All Users Test ---")
for u in User.objects.all():
    m = getattr(u.profile, 'mobile_number', 'N/A') if hasattr(u, 'profile') else 'No Profile'
    pwd_match = u.check_password('anirudha')
    print(f"User: {u.username} | Email: {u.email} | Mobile: {m} | Password Match: {pwd_match}")
