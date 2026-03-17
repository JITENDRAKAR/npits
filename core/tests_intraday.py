from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from core.models import Instrument, Portfolio, Transaction, PnLStatement
from core.views import sell_stock
from decimal import Decimal
from django.utils import timezone
import datetime
from django.contrib.messages.storage.base import BaseStorage

class MockMessageStorage(BaseStorage):
    def __init__(self, request, *args, **kwargs):
        self._queued_messages = []
        super().__init__(request, *args, **kwargs)
    def _get(self, *args, **kwargs):
        return self._queued_messages, True
    def _store(self, messages, *args, **kwargs):
        self._queued_messages.extend(messages)
        return []

class IntradayTradeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.factory = RequestFactory()
        self.inst = Instrument.objects.create(symbol='TEST', name='Test Stock', is_verified=True)

    def _post_sell(self, data):
        request = self.factory.post('/portfolio/sell/', data)
        request.user = self.user
        setattr(request, '_messages', MockMessageStorage(request))
        return sell_stock(request)

    def test_standard_fifo(self):
        """Standard FIFO: Buy Day 1, Buy Day 2, Sell Day 3. Should use Day 1 buy."""
        day1 = timezone.now().date() - datetime.timedelta(days=2)
        day2 = timezone.now().date() - datetime.timedelta(days=1)
        day3 = timezone.now().date()

        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('100'), date=day1)
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('120'), date=day2)
        Portfolio.objects.create(user=self.user, instrument=self.inst, quantity=20, avg_cost=Decimal('110'), ltp=Decimal('120'))

        self._post_sell({'symbol': 'TEST', 'quantity': '10', 'price': '150', 'exit_date': day3.isoformat()})
        
        pnl = PnLStatement.objects.get(user=self.user, instrument=self.inst)
        self.assertEqual(pnl.realized_profit, Decimal('500'))
        
        remaining_tx = Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', remaining_quantity__gt=0)
        self.assertEqual(remaining_tx.date, day2)

    def test_intraday_match(self):
        """Intraday Match: Buy Day 1, Buy Day 2, Sell Day 2 (same volume as Buy 2). Should use Day 2 buy."""
        day1 = timezone.now().date() - datetime.timedelta(days=1)
        day2 = timezone.now().date()

        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('100'), date=day1)
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('120'), date=day2)
        Portfolio.objects.create(user=self.user, instrument=self.inst, quantity=20, avg_cost=Decimal('110'), ltp=Decimal('120'))

        self._post_sell({'symbol': 'TEST', 'quantity': '10', 'price': '150', 'exit_date': day2.isoformat()})
        
        pnl = PnLStatement.objects.get(user=self.user, instrument=self.inst)
        self.assertEqual(pnl.realized_profit, Decimal('300'))
        
        remaining_tx = Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', remaining_quantity__gt=0)
        self.assertEqual(remaining_tx.date, day1)

    def test_volume_mismatch_fallback_to_fifo(self):
        """Volume Mismatch: Buy Day 1 (10). Buy Day 2 (10). Sell Day 2 (5). Should fallback to FIFO (Day 1)."""
        day1 = timezone.now().date() - datetime.timedelta(days=1)
        day2 = timezone.now().date()

        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('100'), date=day1)
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('120'), date=day2)
        Portfolio.objects.create(user=self.user, instrument=self.inst, quantity=20, avg_cost=Decimal('110'), ltp=Decimal('120'))

        self._post_sell({'symbol': 'TEST', 'quantity': '5', 'price': '150', 'exit_date': day2.isoformat()})
        
        pnl = PnLStatement.objects.get(user=self.user, instrument=self.inst)
        self.assertEqual(pnl.realized_profit, Decimal('250'))
        
        day1_tx = Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', date=day1)
        self.assertEqual(day1_tx.remaining_quantity, 5)

    def test_multiple_same_day_buys_find_exact_match(self):
        """Multiple same-day buys: Find the one with exact matching volume."""
        day1 = timezone.now().date() - datetime.timedelta(days=1)
        day2 = timezone.now().date()

        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('100'), date=day1)
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('120'), date=day2)
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=20, remaining_quantity=20, price=Decimal('130'), date=day2)
        
        Portfolio.objects.create(user=self.user, instrument=self.inst, quantity=40, avg_cost=Decimal('120'), ltp=Decimal('130'))

        self._post_sell({'symbol': 'TEST', 'quantity': '20', 'price': '150', 'exit_date': day2.isoformat()})
        
        pnl = PnLStatement.objects.get(user=self.user, instrument=self.inst)
        self.assertEqual(pnl.realized_profit, Decimal('400'))
        
        self.assertEqual(Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', date=day1).remaining_quantity, 10)
        self.assertEqual(Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', date=day2, quantity=10).remaining_quantity, 10)
        self.assertEqual(Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', date=day2, quantity=20).remaining_quantity, 0)
