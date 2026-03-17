from django.db import models
from django.contrib.auth.models import User

class Instrument(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20, unique=True)
    isin = models.CharField(max_length=20, unique=True, null=True, blank=True)

    def __str__(self):
        return self.symbol

class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    avg_cost = models.DecimalField(max_digits=10, decimal_places=2)
    ltp = models.DecimalField(max_digits=10, decimal_places=2) # Last Traded Price
    
    # Calculated fields can be methods or properties, but we'll store them if needed for querying
    # Per requirements: Invested Amount = Quantity * Average Cost
    # Current Value = Quantity * LTP
    
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
