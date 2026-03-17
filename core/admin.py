from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
import pandas as pd
from .models import (
    Instrument, Portfolio, PnLStatement, Profile, OTP, 
    Transaction, SignupOTP, MarketTicker, Strategy, 
    StrategyStock, Watchlist, Dividend, InvestmentGoal,
    CorporateAction
)

class CsvImportForm(forms.Form):
    csv_file = forms.FileField()

@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'isin', 'is_verified', 'last_price')
    search_fields = ('symbol', 'name', 'isin')
    list_filter = ('is_verified',)

    change_list_template = "admin/instrument_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            if not csv_file.name.endswith('.csv') and not csv_file.name.endswith('.xlsx'):
                messages.error(request, 'Only .csv or .xlsx files are allowed')
                return redirect("..")
            
            try:
                if csv_file.name.endswith('.csv'):
                    df = pd.read_csv(csv_file)
                else:
                    df = pd.read_excel(csv_file)
                
                # Required Fields: Company Name, NSE/BSE Code
                df.columns = [c.strip() for c in df.columns]
                
                required_cols = ['Company Name', 'NSE/BSE Code']
                if not all(col in df.columns for col in required_cols):
                    messages.error(request, f"Missing required columns: {required_cols}")
                    return redirect("..")

                count = 0
                for _, row in df.iterrows():
                    name = str(row['Company Name']).strip()
                    symbol = str(row['NSE/BSE Code']).strip().upper()
                    
                    if symbol:
                        Instrument.objects.update_or_create(
                            symbol=symbol,
                            defaults={
                                'name': name,
                                'is_verified': True
                            }
                        )
                        count += 1
                
                self.message_user(request, f"Successfully imported {count} verified instruments.")
                return redirect("..")
            except Exception as e:
                self.message_user(request, f"Error importing: {e}", level=messages.ERROR)
                return redirect("..")

        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'quantity', 'avg_cost', 'ltp')
    search_fields = ('user__username', 'instrument__symbol')
    list_filter = ('user',)

@admin.register(PnLStatement)
class PnLStatementAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'realized_profit', 'exit_date')
    search_fields = ('user__username', 'instrument__symbol')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'investor_type')
    search_fields = ('user__username', 'full_name')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'transaction_type', 'quantity', 'price', 'date')
    list_filter = ('transaction_type', 'date')
    search_fields = ('user__username', 'instrument__symbol')

@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'updated_at')

@admin.register(StrategyStock)
class StrategyStockAdmin(admin.ModelAdmin):
    list_display = ('strategy', 'symbol', 'order')
    list_filter = ('strategy',)

@admin.register(MarketTicker)
class MarketTickerAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'change', 'updated_at')

@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'added_at')
    list_filter = ('user',)

@admin.register(Dividend)
class DividendAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'amount', 'received_date')
    list_filter = ('user', 'received_date')

@admin.register(InvestmentGoal)
class InvestmentGoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'target_amount', 'current_amount', 'target_date')
    list_filter = ('user', 'target_date')

@admin.register(CorporateAction)
class CorporateActionAdmin(admin.ModelAdmin):
    list_display = ('instrument', 'action_type', 'announcement_date')
    list_filter = ('action_type', 'announcement_date')
    search_fields = ('instrument__symbol',)

admin.site.register(OTP)
admin.site.register(SignupOTP)
