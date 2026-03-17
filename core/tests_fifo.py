from django.test import TestCase, Client
from django.contrib.auth.models import User
from core.models import Instrument, Portfolio, Transaction, PnLStatement
from decimal import Decimal
from django.urls import reverse

class FIFOTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        self.client.login(username='testuser', password='password123')
        self.inst = Instrument.objects.create(symbol='TEST', name='Test Stock', is_verified=True)

    def test_fifo_profit_calculation(self):
        # 1. Buy 10 units @ 100
        response = self.client.post(reverse('buy_stock'), {'symbol': 'TEST', 'quantity': 10, 'price': '100'}, follow=True)
        self.assertEqual(response.status_code, 200)
        # 2. Buy 10 units @ 120
        response = self.client.post(reverse('buy_stock'), {'symbol': 'TEST', 'quantity': 10, 'price': '120'}, follow=True)
        self.assertEqual(response.status_code, 200)
        
        portfolio = Portfolio.objects.get(user=self.user, instrument=self.inst)
        self.assertEqual(portfolio.quantity, 20)
        self.assertEqual(portfolio.avg_cost, Decimal('110'))

        # 3. Sell 15 units @ 150
        response = self.client.post(reverse('sell_stock'), {'symbol': 'TEST', 'quantity': 15, 'price': '150'}, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Expected Profit calculation:
        # First 10 units: 10 * (150 - 100) = 500
        # Next 5 units: 5 * (150 - 120) = 150
        # Total Realized Profit: 650
        
        pnl = PnLStatement.objects.get(user=self.user, instrument=self.inst)
        self.assertEqual(pnl.realized_profit, Decimal('650'))
        
        # Remaining Portfolio
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.quantity, 5)
        # Average cost of remaining 5 units should be 120
        self.assertEqual(portfolio.avg_cost, Decimal('120'))
        
        # Remaining transactions
        remaining_tx = Transaction.objects.get(user=self.user, instrument=self.inst, remaining_quantity__gt=0)
        self.assertEqual(remaining_tx.remaining_quantity, 5)
        self.assertEqual(remaining_tx.price, Decimal('120'))
