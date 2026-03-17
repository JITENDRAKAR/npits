from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User

class Instrument(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=50, unique=True)
    isin = models.CharField(max_length=50, unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    last_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    price_change = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    pe_ratio = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    diff_from_lh_pct = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.symbol

    def save(self, *args, **kwargs):
        if self.symbol:
            self.symbol = self.symbol.strip().upper()
        super().save(*args, **kwargs)

class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    avg_cost = models.DecimalField(max_digits=10, decimal_places=2)
    ltp = models.DecimalField(max_digits=10, decimal_places=2) # Last Traded Price
    
    @property
    def invested_amount(self):
        return self.quantity * self.avg_cost

    @property
    def current_value(self):
        return self.quantity * self.ltp

    @property
    def unrealized_pnl(self):
        return self.current_value - self.invested_amount
        
    @property
    def unrealized_pnl_percentage(self):
        if self.invested_amount == 0:
            return 0
        return (self.unrealized_pnl / self.invested_amount) * 100

    class Meta:
        unique_together = ('user', 'instrument')

class PnLStatement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    entry_date = models.DateField(null=True, blank=True)
    exit_date = models.DateField()
    quantity = models.IntegerField()
    buy_value = models.DecimalField(max_digits=15, decimal_places=2)
    sell_value = models.DecimalField(max_digits=15, decimal_places=2)
    realized_profit = models.DecimalField(max_digits=15, decimal_places=2)
    
    
    def __str__(self):
        return f"{self.user.username} - {self.instrument.symbol} - {self.realized_profit}"
        return f"{self.user.username} - {self.instrument.symbol} - {self.realized_profit}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    mobile_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M','Male'),('F','Female')], null=True, blank=True)
    investor_type = models.CharField(max_length=20, choices=[('conservative','Conservative'),('moderate','Moderate'),('growth','Growth'),('aggressive','Aggressive')], default='moderate')

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_max_investment(self, strategy_key):
        """Return maximum investment per stock/ETF for the given strategy based on investor_type.
        strategy_key corresponds to the keys used in STRATEGY_SHEET_TABS (flexi, quant, pyramid, growth).
        """
        mapping = {
            'conservative': {'flexi': 30000, 'pyramid': 15000, 'quant': 10000, 'growth': 5000},
            'moderate': {'flexi': 15000, 'pyramid': 15000, 'quant': 15000, 'growth': 15000},
            'growth': {'flexi': 10000, 'pyramid': 15000, 'quant': 20000, 'growth': 30000},
            'aggressive': {'flexi': 5000, 'pyramid': 15000, 'quant': 30000, 'growth': 50000},
        }
        return mapping.get(self.investor_type, mapping['moderate']).get(strategy_key, 15000)

# Signals to automatically create/save Profile
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, raw, **kwargs):
    if raw:
        return
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, raw, **kwargs):
    if raw:
        return
    if hasattr(instance, 'profile'):
        instance.profile.save()

import logging
logger = logging.getLogger(__name__)

from django.db.models.signals import pre_save
@receiver(pre_save, sender=User)
def track_password_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_user = User.objects.get(pk=instance.pk)
            if old_user.password != instance.password:
                logger.info(f"Password changing for user {instance.username}: {old_user.password[:10]} -> {instance.password[:10]}")
                
                # SHIELD: If user had a usable password, and it's being set to UNUSABLE (starts with !),
                # and this is NOT a deliberate logout/unusable set we expect, restore it.
                if not old_user.password.startswith('!') and instance.password.startswith('!'):
                    logger.warning(f"Restoring usable password for {instance.username} (was about to be set to unusable)")
                    instance.password = old_user.password
        except User.DoesNotExist:
            pass

from allauth.socialaccount.signals import social_account_added, social_account_updated
@receiver(social_account_added)
@receiver(social_account_updated)
def protect_password_on_social_link(request, sociallogin, **kwargs):
    user = sociallogin.user
    if user.pk:
        # Check if user had a usable password before (this is tricky because signal is 'added')
        # But we can at least log it.
        logger.info(f"Social account linked/updated for {user.username}. Provider: {sociallogin.account.provider}")
class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        from django.utils import timezone
        import datetime
        # Valid for 10 minutes
        return self.created_at >= timezone.now() - datetime.timedelta(minutes=10)

    def __str__(self):
        return f"OTP for {self.user.username} - {self.code}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [('BUY', 'Buy'), ('SELL', 'Sell')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    remaining_quantity = models.IntegerField(default=0) # Only for BUY
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'created_at']

    def __str__(self):
        return f"{self.user.username} {self.transaction_type} {self.quantity} {self.instrument.symbol} @ {self.price} on {self.date}"


class SignupOTP(models.Model):
    """OTP sent to an email address BEFORE a user account is created."""
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return self.created_at >= timezone.now() - timedelta(minutes=10)

    def __str__(self):
        return f"SignupOTP for {self.email} - {self.code}"

class MarketTicker(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    change = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Strategy(models.Model):
    name = models.CharField(max_length=50, unique=True) # e.g., 'flexi', 'quant', 'pyramid', 'growth'
    display_name = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

class StrategyStock(models.Model):
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='stocks')
    symbol = models.CharField(max_length=20) # We store symbol string to avoid hard dependency on Instrument object during sync if it doesn't exist yet
    order = models.IntegerField(default=0)

    class Meta:
        unique_together = ('strategy', 'symbol')
        ordering = ['order']

    def __str__(self):
        return f"{self.strategy.name} - {self.symbol}"

class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlists')
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'instrument')

    def __str__(self):
        return f"{self.user.username} watching {self.instrument.symbol}"

class Dividend(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dividends')
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    ex_date = models.DateField(null=True, blank=True)
    received_date = models.DateField()
    
    def __str__(self):
        return f"{self.user.username} - {self.instrument.symbol} - {self.amount}"

class InvestmentGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=20, decimal_places=2)
    target_date = models.DateField()
    current_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.name}"

class CorporateAction(models.Model):
    ACTION_TYPES = [('SPLIT', 'Stock Split'), ('BONUS', 'Bonus Issue'), ('DIVIDEND', 'Dividend Declared'), ('MERGER', 'Merger/Demerger')]
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name='corporate_actions')
    action_type = models.CharField(max_length=10, choices=ACTION_TYPES)
    ratio_numerator = models.IntegerField(null=True, blank=True) # e.g., 2 for a 2:1 split
    ratio_denominator = models.IntegerField(null=True, blank=True) # e.g., 1 for a 2:1 split
    announcement_date = models.DateField()
    record_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.instrument.symbol} - {self.action_type} - {self.announcement_date}"

class SignalNotificationState(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='signal_notification_state')
    last_buy_count = models.IntegerField(default=0)
    last_reduce_count = models.IntegerField(default=0)
    last_sell_count = models.IntegerField(default=0)
    last_signals_hash = models.CharField(max_length=64, null=True, blank=True)
    last_notified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Buy:{self.last_buy_count} Reduce:{self.last_reduce_count} Sell:{self.last_sell_count}"
