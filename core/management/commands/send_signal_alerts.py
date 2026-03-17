from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from core.models import SignalNotificationState
from core.utils import get_recommendations
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Checks portfolio signal counts and sends styled email alerts to users if their counts have changed.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sending emails even if signal counts haven\'t changed',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        users = User.objects.filter(is_active=True)
        emails_sent = 0
        
        for user in users:
            try:
                if not hasattr(user, 'profile') or not user.email:
                    continue  # Skip users without profiles or emails

                # Get Current Recommendation Totals
                recommendations, realized_profits, strategy_stocks = get_recommendations(user)
                
                # Replicate exactly the context_processors / dashboard logic
                # Include items currently in portfolio OR P&L Buybacks
                user_signals = [
                    r for r in recommendations 
                    if r.get('in_portfolio', False) or (r.get('action') == 'BUY' and r.get('realized_profit', 0) > 0)
                ]
                
                current_buy = sum(1 for r in user_signals if r.get('action') == 'BUY')
                current_reduce = sum(1 for r in user_signals if r.get('action') == 'REDUCE')
                current_sell = sum(1 for r in user_signals if r.get('action') == 'SELL')
                total_current = current_buy + current_reduce + current_sell

                # Get or Create Notification State
                state, created = SignalNotificationState.objects.get_or_create(
                    user=user,
                    defaults={
                        'last_buy_count': current_buy,
                        'last_reduce_count': current_reduce,
                        'last_sell_count': current_sell
                    }
                )

                # Has anything changed?
                # If newly created, we technically haven't sent them an email before, so we MIGHT want to send an initial one.
                # However, to avoid spamming everyone on day 1, we only trigger on ACTUAL changes.
                has_changed = (
                    state.last_buy_count != current_buy or 
                    state.last_reduce_count != current_reduce or 
                    state.last_sell_count != current_sell
                )

                if (has_changed or force) and total_current > 0:
                    # Prepare Email Template
                    subject = "Action Required: Your Portfolio Signal Alerts Have Changed"
                    site_url = getattr(settings, 'SITE_URL', 'https://npits.in') # Use live domain
                    
                    context = {
                        'user': user,
                        'buy_count': current_buy,
                        'reduce_count': current_reduce,
                        'sell_count': current_sell,
                        'total_count': total_current,
                        'site_url': site_url
                    }

                    html_message = render_to_string('emails/signal_alert.html', context)
                    plain_message = strip_tags(html_message)

                    # Send Email
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        from_email=f"Net Profit <{settings.EMAIL_HOST_USER}>",
                        recipient_list=[user.email],
                        html_message=html_message,
                        fail_silently=False,
                    )

                    # Update State Tracking
                    state.last_buy_count = current_buy
                    state.last_reduce_count = current_reduce
                    state.last_sell_count = current_sell
                    state.save()
                    
                    emails_sent += 1
                    self.stdout.write(self.style.SUCCESS(f'Successfully sent signal alert to {user.email}'))
                    
            except Exception as e:
                logger.error(f"Failed to process signal alerts for {user.username}: {e}")
                self.stdout.write(self.style.ERROR(f'Error processing user {user.username}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Completed processing. Emails sent: {emails_sent}'))
