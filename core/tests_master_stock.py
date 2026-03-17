from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Instrument, Portfolio

class MasterStockDatabaseTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        self.client.login(username='testuser', password='password123')
        
        # Create verified instruments
        self.inst1 = Instrument.objects.create(name='Reliance Industries', symbol='RELIANCE', is_verified=True)
        self.inst2 = Instrument.objects.create(name='Tata Consultancy Services', symbol='TCS', is_verified=True)
        self.inst3 = Instrument.objects.create(name='Unverified Stock', symbol='WRONG', is_verified=False)

    def test_search_instruments_api(self):
        # Search by name
        response = self.client.get(reverse('search_instruments'), {'q': 'Reli'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['symbol'], 'RELIANCE')

        # Search by symbol
        response = self.client.get(reverse('search_instruments'), {'q': 'TCS'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Tata Consultancy Services')

        # Unverified should not appear
        response = self.client.get(reverse('search_instruments'), {'q': 'WRONG'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 0)

    def test_add_portfolio_validation(self):
        # Valid verified stock
        response = self.client.post(reverse('add_portfolio_item'), {
            'company_name': 'Reliance Industries',
            'symbol': 'RELIANCE',
            'quantity': 10,
            'avg_cost': 2500,
        })
        self.assertEqual(response.status_code, 302) # Redirect to dashboard
        self.assertTrue(Portfolio.objects.filter(instrument__symbol='RELIANCE').exists())

        # Invalid unverified stock
        response = self.client.post(reverse('add_portfolio_item'), {
            'company_name': 'Wrong Stock',
            'symbol': 'WRONG',
            'quantity': 10,
            'avg_cost': 100,
        })
        self.assertEqual(response.status_code, 200) # Form redisplays
        # Check that it didn't create a portfolio item
        self.assertFalse(Portfolio.objects.filter(instrument__symbol='WRONG').exists())
