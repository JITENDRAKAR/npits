from django.core.management.base import BaseCommand
from core.models import Portfolio, Instrument
from core.utils import fetch_live_ltp
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update LTP for all portfolios from Google Sheet'

    def handle(self, *args, **options):
        self.stdout.write("Fetching live LTP data...")
        ltp_map = fetch_live_ltp()
        
        if not ltp_map:
            self.stderr.write(self.style.ERROR("Failed to fetch LTP data from Google Sheet."))
            return

        self.stdout.write(f"Fetched {len(ltp_map)} symbol prices.")
        
        updated_count = 0
        all_portfolios = Portfolio.objects.select_related('instrument').all()
        
        from django.db import transaction
        with transaction.atomic():
            for portfolio in all_portfolios:
                symbol = portfolio.instrument.symbol.upper()
                if symbol in ltp_map:
                    ltp_data = ltp_map[symbol]
                    new_ltp = ltp_data[0] if isinstance(ltp_data, tuple) else ltp_data
                    if float(portfolio.ltp) != float(new_ltp):
                        portfolio.ltp = new_ltp
                        portfolio.save(update_fields=['ltp'])
                        updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} portfolio records."))
