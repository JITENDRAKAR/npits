import os
import django
import sys

# Set up Django environment
sys.path.append('c:\\inetpub\\wwwroot\\NPITS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Transaction, PnLStatement, User, Instrument
from django.db import transaction

def backfill_entry_dates():
    users = User.objects.all()
    total_updated = 0

    for user in users:
        print(f"Processing user: {user.username}")
        # Get all instruments traded by this user
        instrument_ids = Transaction.objects.filter(user=user).values_list('instrument_id', flat=True).distinct()
        
        for inst_id in instrument_ids:
            inst = Instrument.objects.get(id=inst_id)
            # Fetch all transactions for this user/instrument in chronological order
            txs = Transaction.objects.filter(user=user, instrument=inst).order_by('date', 'created_at')
            
            # Fetch all P&L statements for this user/instrument
            pnl_statements = list(PnLStatement.objects.filter(user=user, instrument=inst).order_by('exit_date', 'id'))
            pnl_idx = 0
            
            buy_queue = [] # List of (date, quantity)
            
            for tx in txs:
                if tx.transaction_type == 'BUY':
                    buy_queue.append({'date': tx.date, 'qty': tx.quantity})
                else:
                    # It's a SELL transaction. Match it with the next PnLStatement
                    if pnl_idx < len(pnl_statements):
                        pnl = pnl_statements[pnl_idx]
                        
                        # Use FIFO to find the entry date for this sell
                        remaining_to_sell = tx.quantity
                        entry_date = None
                        
                        temp_buy_queue = []
                        for buy in buy_queue:
                            if remaining_to_sell <= 0:
                                temp_buy_queue.append(buy)
                                continue
                                
                            if entry_date is None:
                                entry_date = buy['date']
                            
                            consumed = min(buy['qty'], remaining_to_sell)
                            buy['qty'] -= consumed
                            remaining_to_sell -= consumed
                            
                            if buy['qty'] > 0:
                                temp_buy_queue.append(buy)
                        
                        buy_queue = temp_buy_queue
                        
                        # Update the PnLStatement
                        if pnl.entry_date is None and entry_date is not None:
                            pnl.entry_date = entry_date
                            pnl.save()
                            total_updated += 1
                        
                        pnl_idx += 1

    print(f"Backfill complete. Updated {total_updated} P&L records.")

if __name__ == "__main__":
    with transaction.atomic():
        backfill_entry_dates()
