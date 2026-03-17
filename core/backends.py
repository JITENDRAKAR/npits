from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Profile

User = get_user_model()

import logging
logger = logging.getLogger(__name__)

class EmailOrMobileBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        logger.debug(f"Attempting authenticate for: {username}")
        if username is None:
            username = kwargs.get('username')
        try:
            # Check if the username is an email, mobile number, or actual username
            # We first try to get the user based on these fields
            user = User.objects.filter(
                Q(username__iexact=username) | 
                Q(email__iexact=username) | 
                Q(profile__mobile_number=username)
            ).first()
            
        except Exception:
            return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
