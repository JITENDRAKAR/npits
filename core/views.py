from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from .forms import (
    UploadFileForm, PortfolioForm, ManualPortfolioForm, 
    CustomUserCreationForm, ProfileForm, ForgotPasswordForm, 
    VerifyOTPForm, SetPasswordForm, EditLotForm
)
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
try:
    from allauth.account.forms import SetPasswordForm as AllauthSetPasswordForm
except ImportError:
    AllauthSetPasswordForm = DjangoSetPasswordForm
from .models import Portfolio, PnLStatement, Instrument, Profile, OTP, Transaction, SignupOTP, MarketTicker, Strategy
from .utils import fetch_live_ltp, perform_sync, get_recommendations, fetch_strategy_stocks
import random
import json
import yfinance as yf
import pandas as pd
import math
from decimal import Decimal

@login_required
def forgot_password_session(request):
    user = request.user
    if not user.email:
        messages.error(request, "No email address found for your account. Please update your profile.")
        return redirect('edit_profile')
    
    # Generate 6-digit OTP
    code = str(random.randint(100000, 999999))
    
    # Save OTP
    OTP.objects.filter(user=user).delete()
    OTP.objects.create(user=user, code=code)
    
    # Send Email
    try:
        subject = "Your Password Reset Code"
        message = f"Your 6-digit verification code is: {code}\nThis code is valid for 10 minutes."
        send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])
        
        # Store email in session for next steps
        request.session['reset_email'] = user.email
        messages.success(request, f"A 6-digit code has been sent to {user.email}")
        return redirect('verify_otp')
    except Exception as e:
        logger.error(f"Error sending email: {type(e).__name__}: {e}")
        messages.error(request, f"Failed to send email. Please try again later.")
        return redirect('password_change')

def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            # Generate 6-digit OTP
            code = str(random.randint(100000, 999999))
            
            # Save OTP
            OTP.objects.filter(user=user).delete() # Delete old ones
            OTP.objects.create(user=user, code=code)
            
            # Send Email
            try:
                subject = "Your Password Reset Code"
                message = f"Your 6-digit verification code is: {code}\nThis code is valid for 10 minutes."
                send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
                
                # Store email in session for next steps
                request.session['reset_email'] = email
                messages.success(request, f"A 6-digit code has been sent to {email}")
                return redirect('verify_otp')
            except Exception as e:
                import traceback
                print(f"Error sending email: {type(e).__name__}: {e}")
                traceback.print_exc()
                messages.error(request, f"Failed to send email (Error: {type(e).__name__}). Please try again later.")
    else:
        form = ForgotPasswordForm()
    return render(request, 'registration/forgot_password.html', {'form': form})

def verify_otp(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')
    
    if request.method == 'POST':
        form = VerifyOTPForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp']
            user = User.objects.get(email=email)
            otp_obj = OTP.objects.filter(user=user, code=otp_code).first()
            
            if otp_obj and otp_obj.is_valid():
                request.session['otp_verified'] = True
                return redirect('reset_password')
            else:
                messages.error(request, "Invalid or expired code.")
    else:
        form = VerifyOTPForm()
    return render(request, 'registration/verify_otp.html', {'form': form})

def reset_password(request):
    email = request.session.get('reset_email')
    otp_verified = request.session.get('otp_verified')
    
    if not email or not otp_verified:
        return redirect('forgot_password')
    
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            
            # Cleanup session
            del request.session['reset_email']
            del request.session['otp_verified']
            OTP.objects.filter(user=user).delete()
            
            messages.success(request, "Password has been reset successfully. You can now login.")
            return redirect('login')
    else:
        form = SetPasswordForm()
    return render(request, 'registration/reset_password.html', {'form': form})

class CustomPasswordChangeView(PasswordChangeView):
    def get_form_class(self):
        # Determine if the user needs to set a password (no usable password or social account)
        is_social = False
        try:
            from allauth.socialaccount.models import SocialAccount
            if SocialAccount.objects.filter(user=self.request.user).exists():
                is_social = True
        except ImportError:
            pass

        if not self.request.user.has_usable_password() or is_social:
            return AllauthSetPasswordForm
            
        return super().get_form_class()
import pandas as pd
import requests
import io
import datetime
import math
from decimal import Decimal
from django.db.models import Sum
import xml.etree.ElementTree as ET
from dateutil import parser
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.db.models import Sum, F
from django.db.models.functions import Upper

PORTFOLIO_HEADERS = ['Instrument', 'Quantity', 'Average Cost', 'LTP']
PNL_HEADERS = ['Symbol', 'Quantity', 'Buy Value', 'Sell Value', 'Profit', 'Entry Date', 'Exit Date']

STRATEGY_SYMBOLS = {
    'flexi': {
        'HNGSNGBEES', 'GOLDBEES', 'MON100', 'NIFTYBEES', 'SILVERBEES'
    },
    'quant': {
        'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
        'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BHARTIARTL',
        'CIPLA', 'COALINDIA', 'DRREDDY', 'EICHERMOT', 'ETERNAL',
        'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE', 'HINDALCO',
        'HINDUNILVR', 'ICICIBANK', 'ITC', 'INFY', 'INDIGO',
        'JSWSTEEL', 'JIOFIN', 'KOTAKBANK', 'LT', 'M&M',
        'MARUTI', 'MAXHEALTH', 'NTPC', 'NESTLEIND', 'ONGC',
        'POWERGRID', 'RELIANCE', 'SBILIFE', 'SHRIRAMFIN', 'SBIN',
        'SUNPHARMA', 'TCS', 'TATACONSUM', 'TMPV', 'TATASTEEL',
        'TECHM', 'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO'
    },
    'pyramid': {
        'HEALTHY', 'BFSI', 'METALIETF', 'HDFCSML250', 'INFRABEES',
        'PHARMABEES', 'JUNIORBEES', 'ALPHA', 'MAFANG', 'MID150BEES',
        'ITBEES', 'MODEFENCE', 'MOVALUE', 'SMALLCAP', 'BANKBEES',
        'OILIETF', 'AUTOIETF', 'MOREALTY', 'CPSEETF', 'PSUBANK',
        'CONSUMBEES', 'LOWVOLIETF', 'MOMENTUM50', 'AXISVALUE', 'HDFCGROWTH'
    }
}

def handle_uploaded_file(f):
    if f.name.endswith('.csv'):
        return pd.read_csv(f)
    elif f.name.endswith('.xlsx'):
        return pd.read_excel(f)
    return None

def clean_numeric(val, to_int=False):
    """
    Clean numeric strings containing commas, currency symbols, and quotes.
    Handles pd.NA/NaN, floats, and ints.
    """
    if pd.isna(val) or val is None:
        return None
    
    if isinstance(val, (int, float)):
        return int(val) if to_int else float(val)
    
    if isinstance(val, str):
        # Remove commas, currency symbols, and various quotes
        cleaned = val.replace(',', '').replace('₹', '').replace('"', '').replace("'", "")
        # Handle smart quotes and other potential non-numeric junk
        cleaned = cleaned.replace('“', '').replace('”', '').replace('‘', '').replace('’', '').strip()
        
        if not cleaned:
            return None
        
        try:
            return int(float(cleaned)) if to_int else float(cleaned)
        except (ValueError, TypeError):
            return None
    return None

# Removed fetch_live_ltp from here as it is now in core.utils

def fetch_market_data():
    """Fetch market ticker data from MarketTicker model."""
    market_list = []
    tickers = MarketTicker.objects.all()
    for t in tickers:
        market_list.append({
            'name': t.name,
            'price': t.price,
            'change': t.change,
            'symbol': t.name.upper().split(' ')[0] # Heuristic: use first word of name as symbol
        })
    return market_list

SHEET_ID = "12eLJHTlHO1naQgJ-dzf-UTgUbasVv02tgwlHKofG2Y4"

STRATEGY_SHEET_TABS = {
    'flexi': 'FlexiMultiInvest',
    'quant': 'NiftyQuant',
    'pyramid': 'Pyramiding',
    'growth': 'ReinvestX',
}



def fetch_rss_feed(url, source_name, timeout=10):
    """Generic RSS fetcher with source-specific handling."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Handle potential encoding issues
        response.encoding = 'utf-8'
        
        root = ET.fromstring(response.content)
        items = []
        for item in root.findall('.//item'):
            try:
                title_node = item.find('title')
                link_node = item.find('link')
                pub_date_node = item.find('pubDate')
                
                title = title_node.text if title_node is not None else "No Title"
                link = link_node.text if link_node is not None else "#"
                pub_date_str = pub_date_node.text if pub_date_node is not None else ""
                
                description_node = item.find('description')
                description = description_node.text if description_node is not None else ""
                if description:
                    import re
                    description = re.sub('<[^<]+?>', '', description)
                
                items.append({
                    'source': source_name,
                    'title': title,
                    'link': link,
                    'pub_date': pub_date_str,
                    'description': description[:150] + "..." if len(description or "") > 150 else (description or "")
                })
            except Exception as e:
                print(f"Error parsing item in {source_name}: {e}")
                continue
        return items
    except Exception as e:
        print(f"Error fetching {source_name} feed: {e}")
        return []

def fetch_landing_data():
    """Fetch all RSS feeds for the landing page with caching."""
    cache_key = 'landing_rss_data_v3'  # v3: Livemint + Zerodha Pulse
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    # Left tile: Livemint Markets RSS
    nse_news = fetch_rss_feed('https://www.livemint.com/rss/markets', 'Livemint')
    
    # Financial News - Zerodha Pulse
    pulse_news = fetch_rss_feed('http://pulse.zerodha.com/feed.php', 'Zerodha Pulse')
    
    result = {
        'nse_news': nse_news[:20],
        'financial_news': pulse_news[:20]
    }
    
    if nse_news or pulse_news:
        cache.set(cache_key, result, 1800) # 30 mins
    return result

@ensure_csrf_cookie
def landing(request):
    """Public landing page with marketing content and ticker."""
    market_data = fetch_market_data()
    landing_data = fetch_landing_data()
    context = {
        'market_data': market_data,
        'nse_news': landing_data.get('nse_news', []),
        'financial_news': landing_data.get('financial_news', []),
        'last_updated': datetime.datetime.now(),
    }
    return render(request, 'core/landing.html', context)

@ensure_csrf_cookie
def strategy(request):
    """Investment strategy detail page with recommended stocks from Google Sheets."""
    strategy_stocks = fetch_strategy_stocks()
    
    # Identify "Others" stocks for the current user and calculate allocation
    others_stocks = []
    allocation_data = {
        'FlexiMultiInvest': 0,
        'NiftyQuant': 0,
        'Pyramiding': 0,
        'ReinvestX': 0,
        'Others': 0
    }
    
    if request.user.is_authenticated:
        # Get all symbols from strategy marquees
        all_strategy_symbols = set()
        symbol_to_strategy = {}
        
        # Map internal keys to display names for the graph
        strategy_labels = {
            'flexi': 'FlexiMultiInvest',
            'quant': 'NiftyQuant',
            'pyramid': 'Pyramiding',
            'growth': 'ReinvestX'
        }
        
        for s_key, s_list in strategy_stocks.items():
            for sym in s_list:
                sym_upper = sym.upper()
                all_strategy_symbols.add(sym_upper)
                symbol_to_strategy[sym_upper] = s_key
        
        # Get user's active portfolio
        portfolio_items = Portfolio.objects.filter(
            user=request.user, 
            quantity__gt=0
        ).select_related('instrument')
        
        user_portfolio_symbols = set()
        for item in portfolio_items:
            symbol = item.instrument.symbol.upper()
            user_portfolio_symbols.add(symbol)
            
            # Use invested_amount property from Portfolio model
            invested = float(item.invested_amount)
            
            s_key = symbol_to_strategy.get(symbol)
            if s_key in strategy_labels:
                allocation_data[strategy_labels[s_key]] += invested
            else:
                allocation_data['Others'] += invested
        
        # Others list for marquee = Portfolio stocks not in any strategy marquee
        others_stocks = sorted(list(user_portfolio_symbols - all_strategy_symbols))

    # Prepare labels and data for Chart.js
    chart_labels = list(allocation_data.keys())
    chart_values = list(allocation_data.values())
    has_investments = sum(chart_values) > 0

    context = {
        'flexi_stocks': strategy_stocks.get('flexi', []),
        'quant_stocks': strategy_stocks.get('quant', []),
        'pyramid_stocks': strategy_stocks.get('pyramid', []),
        'growth_stocks': strategy_stocks.get('growth', []),
        'others_stocks': others_stocks,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'has_investments': has_investments,
    }
    return render(request, 'core/strategy.html', context)

def mf_guide(request):
    """Mutual Fund Guide page."""
    return render(request, 'core/mf_guide.html')

def stock_guide(request):
    """Stock Guide page."""
    return render(request, 'core/stock_guide.html')

def etf_guide(request):
    """ETF Guide page."""
    return render(request, 'core/etf_guide.html')

def nps_guide(request):
    """NPS Guide page."""
    return render(request, 'core/nps_guide.html')

def donation(request):
    """Donation page."""
    return render(request, 'core/donation.html')

def about_project(request):
    """Project Report Page."""
    return render(request, 'core/about_project.html')

@login_required
def dashboard(request):
    recommendations, realized_profits, strategy_stocks = get_recommendations(request.user)
    
    total_invested = 0
    total_current_value = 0
    total_unrealized_pnl = 0
        
    total_realized_profit = sum(realized_profits.values())

    # Strategy-based Filtering
    all_strategy_stocks = fetch_strategy_stocks()
    current_strategy = request.GET.get('strategy')
    
    # Flatten all strategy symbols for easy lookup
    all_known_strategy_symbols = set()
    for s_list in all_strategy_stocks.values():
        all_known_strategy_symbols.update(s_list)
    
    # Filter recommendations based on current strategy
    if current_strategy:
        filtered_recommendations = []
        if current_strategy == 'others':
            # Show only stocks NOT in any strategy list
            for r in recommendations:
                if r['symbol'].upper() not in all_known_strategy_symbols:
                    filtered_recommendations.append(r)
        else:
            # Show only stocks in the specific strategy list
            target_list = all_strategy_stocks.get(current_strategy, [])
            for r in recommendations:
                if r['symbol'].upper() in target_list:
                    filtered_recommendations.append(r)
        recommendations = filtered_recommendations
    else:
        # Default view: show portfolio items PLUS all strategy signals
        recommendations = [
            r for r in recommendations 
            if r.get('in_portfolio', False) or r.get('action') in ['BUY', 'SELL', 'REDUCE']
        ]

    # Recalculate totals based on the filtered view
    total_invested = sum(r['invested_amount'] for r in recommendations)
    total_current_value = sum(r['current_value'] for r in recommendations)
    total_unrealized_pnl = sum(r['unrealized_pnl'] for r in recommendations)
    
    total_unrealized_pnl_percent = 0
    if total_invested > 0:
        total_unrealized_pnl_percent = (total_unrealized_pnl / total_invested) * 100
    
    total_day_change = sum(r.get('day_change', 0) for r in recommendations if r.get('in_portfolio'))
    total_day_change_percent = 0
    previous_total_value = total_current_value - total_day_change
    if previous_total_value > 0:
        total_day_change_percent = (total_day_change / previous_total_value) * 100

    if current_strategy and current_strategy != 'others':
        target_list = all_strategy_stocks.get(current_strategy, [])
        total_realized_profit = sum(profit for symbol, profit in realized_profits.items() if symbol.upper() in target_list)
    elif current_strategy == 'others':
        total_realized_profit = sum(profit for symbol, profit in realized_profits.items() if symbol.upper() not in all_known_strategy_symbols)
    else:
        total_realized_profit = sum(realized_profits.values())
        


    # 1. Sell Recommendations: Only SELL actions, sorted by P&L value (unrealized_pnl) desc
    sell_recommendations = [r for r in recommendations if r['action'] == 'SELL']
    sell_recommendations.sort(key=lambda x: x['unrealized_pnl'], reverse=True)

    # 2. Buy Recommendations: Only BUY actions, sorted by buy_gap desc
    buy_recommendations = [r for r in recommendations if r['action'] == 'BUY']
    buy_recommendations.sort(key=lambda x: x['buy_gap'], reverse=True)

    # 3. Reduce Recommendations: Only REDUCE actions, sorted by reduce_gap desc
    reduce_sigs = [r for r in recommendations if r['action'] == 'REDUCE']
    reduce_sigs.sort(key=lambda x: x['reduce_gap'], reverse=True)

    from .models import Strategy, MarketTicker
    last_strategy_update = Strategy.objects.aggregate(models.Max('updated_at'))['updated_at__max']
    last_ticker_update = MarketTicker.objects.aggregate(models.Max('updated_at'))['updated_at__max']
    
    # Get the most recent of the two
    last_updated = last_strategy_update
    if last_ticker_update and (not last_updated or last_ticker_update > last_updated):
        last_updated = last_ticker_update
    
    if not last_updated:
        last_updated = datetime.datetime.now()

    context = {
        'recommendations': recommendations,
        'sell_recommendations': sell_recommendations,
        'buy_recommendations': buy_recommendations,
        'reduce_sigs': reduce_sigs,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_unrealized_pnl_percent': total_unrealized_pnl_percent,
        'total_realized_profit': total_realized_profit,
        'total_day_change': total_day_change,
        'total_day_change_percent': total_day_change_percent,
        'last_updated': last_updated,
        'current_strategy': current_strategy,
    }
    return render(request, 'core/dashboard.html', context)

def search_instruments(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    instruments = Instrument.objects.filter(
        is_verified=True
    ).filter(
        models.Q(name__icontains=query) | models.Q(symbol__icontains=query)
    )[:10]
    
    results = [
        {'id': inst.id, 'name': inst.name, 'symbol': inst.symbol, 'ltp': float(inst.last_price or 0)}
        for inst in instruments
    ]
    return JsonResponse(results, safe=False)

@login_required
def add_portfolio_item(request):
    if request.method == 'POST':
        form = ManualPortfolioForm(request.POST)
        if form.is_valid():
            symbol = form.cleaned_data['symbol'].strip().upper()
            quantity = form.cleaned_data['quantity']
            avg_cost = form.cleaned_data['avg_cost']
            transaction_date = form.cleaned_data.get('date') or timezone.now().date()

            # Get Instrument (must be verified)
            try:
                inst = Instrument.objects.get(symbol__iexact=symbol, is_verified=True)
            except Instrument.DoesNotExist:
                messages.error(request, f"'{symbol}' is not a verified instrument in our database.")
                return render(request, 'core/add_portfolio.html', {'form': form, 'title': 'Add Stock Manually'})

            # Try to get initial LTP from live data if possible
            live_ltps = fetch_live_ltp()
            ltp_data = live_ltps.get(symbol)
            if isinstance(ltp_data, tuple):
                ltp = ltp_data[0]
            else:
                ltp = ltp_data or avg_cost

            # Create Transaction record
            Transaction.objects.create(
                user=request.user,
                instrument=inst,
                transaction_type='BUY',
                quantity=quantity,
                remaining_quantity=quantity,
                price=avg_cost,
                date=transaction_date
            )

            portfolio, created = Portfolio.objects.get_or_create(
                user=request.user, 
                instrument=inst,
                defaults={'quantity': 0, 'avg_cost': Decimal('0'), 'ltp': ltp}
            )
            
            # Update Weighted Average Cost for Portfolio summary
            current_total_cost = Decimal(str(portfolio.quantity)) * portfolio.avg_cost
            new_total_cost = Decimal(str(quantity)) * Decimal(str(avg_cost))
            total_quantity = portfolio.quantity + quantity
            
            new_avg_cost = (current_total_cost + new_total_cost) / Decimal(str(total_quantity))
            
            portfolio.quantity = total_quantity
            portfolio.avg_cost = new_avg_cost
            # Only update LTP if it was 0 or just created
            if created or not portfolio.ltp or portfolio.ltp == 0:
                portfolio.ltp = ltp
            portfolio.save()
            messages.success(request, f"Successfully added/updated {symbol} in your portfolio.")
            return redirect('dashboard')
    else:
        form = ManualPortfolioForm()
    return render(request, 'core/add_portfolio.html', {'form': form, 'title': 'Add Stock Manually'})

@login_required
def upload_portfolio(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            df = handle_uploaded_file(request.FILES['file'])
            if df is not None:
                # Strict Header Validation
                uploaded_headers = list(df.columns)
                if uploaded_headers != PORTFOLIO_HEADERS:
                    messages.error(request, f"Header mismatch. Expected: {PORTFOLIO_HEADERS}. Got: {uploaded_headers}")
                    return redirect('upload_portfolio')

                try:
                    # Fetch live LTPs to prefer over file data if available
                    live_ltps = fetch_live_ltp()
                    
                    # Track aggregated data per symbol: {symbol: {'qty': total_qty, 'cost': weighted_avg_cost, 'ltp': last_ltp, 'instrument': inst_obj}}
                    aggregated_data = {}

                    for idx, row in df.iterrows():
                        symbol = row.get('Instrument')
                        if not symbol:
                            continue
                        
                        clean_symbol = symbol.strip().upper()
                        qty    = clean_numeric(row.get('Quantity'), to_int=True)
                        avg    = clean_numeric(row.get('Average Cost'))
                        
                        # Prefer Live LTP if available, otherwise fallback to file LTP
                        ltp_data = live_ltps.get(clean_symbol)
                        if isinstance(ltp_data, tuple):
                            ltp = float(ltp_data[0])
                        else:
                            ltp = float(ltp_data or clean_numeric(row.get('LTP')) or 0)

                        # Skip rows where symbol or quantity is missing/NaN
                        if not clean_symbol or (isinstance(clean_symbol, float) and math.isnan(clean_symbol)):
                            continue
                        if qty is None or (isinstance(qty, float) and math.isnan(qty)):
                            continue

                        # Get Instrument (must be verified)
                        from core.utils import resolve_instrument
                        inst = resolve_instrument(clean_symbol)
                        if not inst:
                            messages.warning(request, f"Skipped '{symbol}': Not in verified database.")
                            continue

                        # Create Transaction record for each row (lot preservation)
                        Transaction.objects.create(
                            user=request.user,
                            instrument=inst,
                            transaction_type='BUY',
                            quantity=qty,
                            remaining_quantity=qty,
                            price=avg,
                            date=timezone.now().date()
                        )

                        # Aggregate data for Portfolio update
                        if clean_symbol not in aggregated_data:
                            aggregated_data[clean_symbol] = {
                                'qty': qty,
                                'total_cost': Decimal(str(qty)) * Decimal(str(avg)),
                                'ltp': ltp,
                                'instrument': inst
                            }
                        else:
                            aggregated_data[clean_symbol]['qty'] += qty
                            aggregated_data[clean_symbol]['total_cost'] += Decimal(str(qty)) * Decimal(str(avg))
                            # Update LTP only if we have a non-zero one
                            if ltp > 0:
                                aggregated_data[clean_symbol]['ltp'] = ltp

                    # Update Portfolio once per symbol with aggregated totals
                    for symbol, data in aggregated_data.items():
                        qty = data['qty']
                        total_cost = data['total_cost']
                        avg_cost = total_cost / Decimal(str(qty)) if qty > 0 else 0
                        ltp = data['ltp']
                        inst = data['instrument']

                        portfolio, created = Portfolio.objects.get_or_create(
                            user=request.user,
                            instrument=inst,
                            defaults={
                                'quantity': qty,
                                'avg_cost': avg_cost,
                                'ltp': ltp or 0
                            }
                        )
                        if not created:
                            # If it already exists, we replace with the new upload state (which seems to be the intended behavior of upload_portfolio)
                            portfolio.quantity = qty
                            portfolio.avg_cost = avg_cost
                            # Only update LTP if it was 0 or just provided
                            if not portfolio.ltp or portfolio.ltp == 0 or ltp > 0:
                                portfolio.ltp = ltp or portfolio.ltp
                            portfolio.save()

                    messages.success(request, "Portfolio uploaded successfully.")
                    return redirect('dashboard')
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    messages.error(request, f"Upload failed: {type(e).__name__}: {e}")
            else:
                messages.error(request, "Invalid file format. Please upload a .csv or .xlsx file.")
    else:
        form = UploadFileForm()
    return render(request, 'core/upload.html', {'form': form, 'title': 'Upload Portfolio'})

@login_required
def export_portfolio(request):
    """Export the user's portfolio data to an Excel file."""
    from django.http import HttpResponse
    import io
    try:
        recommendations, realized_profits, strategy_stocks = get_recommendations(request.user)
        
        # Filter to show only portfolio items (same as dashboard default view)
        recommendations = [
            r for r in recommendations
            if r.get('in_portfolio', False) or (r.get('action') == 'BUY' and r.get('realized_profit', 0) > 0)
        ]

        # Build rows for export
        rows = []
        for r in recommendations:
            rows.append({
                'Instrument': r.get('name', r.get('symbol', '')),
                'Symbol': r.get('symbol', ''),
                'Quantity': r.get('quantity', 0),
                'Average Cost': round(float(r.get('avg_cost', 0)), 2),
                'LTP': round(float(r.get('ltp', 0)), 2),
                'Day Change': round(float(r.get('day_change', 0)), 2),
                'Day Change %': round(float(r.get('day_change_pct', 0)), 2),
                'Invested Amount': round(float(r.get('invested_amount', 0)), 2),
                'Current Value': round(float(r.get('current_value', 0)), 2),
                'Unrealized P&L': round(float(r.get('unrealized_pnl', 0)), 2),
                'P&L %': round(float(r.get('pnl_percent', 0)), 2),
                'Action': r.get('action', ''),
                'Reason': r.get('reason', ''),
                'Realized Profit': round(float(r.get('realized_profit', 0)), 2),
            })

        df = pd.DataFrame(rows)

        # Write to Excel in memory
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Portfolio')
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="portfolio_export.xlsx"'
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f"Export failed: {type(e).__name__}: {e}")
        return redirect('dashboard')


def upload_pnl(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            df = handle_uploaded_file(request.FILES['file'])
            if df is not None:
                # Strict Header Validation
                uploaded_headers = list(df.columns)
                if uploaded_headers != PNL_HEADERS:
                    messages.error(request, "No matched with Sample Header of data.")
                    return redirect('upload_pnl')

                count = 0
                for _, row in df.iterrows():
                    symbol = row.get('Symbol')
                    qty = clean_numeric(row.get('Quantity'), to_int=True)
                    sell_val = clean_numeric(row.get('Sell Value'))
                    buy_val = clean_numeric(row.get('Buy Value'))
                    profit = clean_numeric(row.get('Profit'))
                    entry_date = row.get('Entry Date')
                    exit_date = row.get('Exit Date')
                    
                    # Basic validation
                    if symbol and qty and profit:
                        # Get Instrument (must be verified)
                        from core.utils import resolve_instrument
                        inst = resolve_instrument(symbol.strip())
                        if not inst:
                            messages.warning(request, f"Skipped '{symbol}': Not in verified database.")
                            continue
                        
                        # Duplicate prevention: Symbol + Quantity + Sell Value
                        exists = PnLStatement.objects.filter(
                            user=request.user,
                            instrument=inst,
                            quantity=qty,
                            sell_value=sell_val
                        ).exists()
                        
                        if not exists:
                            PnLStatement.objects.create(
                                user=request.user,
                                instrument=inst,
                                quantity=qty,
                                buy_value=buy_val or 0,
                                sell_value=sell_val or 0,
                                realized_profit=profit,
                                entry_date=pd.to_datetime(entry_date).date() if entry_date and str(entry_date).lower() != 'nan' else None,
                                exit_date=pd.to_datetime(exit_date).date() if exit_date and str(exit_date).lower() != 'nan' else None
                            )
                            count += 1
                messages.success(request, f"{count} P&L records uploaded.")
                return redirect('dashboard')
    else:
        form = UploadFileForm()
    return render(request, 'core/upload.html', {'form': form, 'title': 'Upload P&L Statement'})

@csrf_exempt
def send_signup_otp(request):
    """AJAX endpoint: sends a 6-digit OTP to the given email (pre-signup)."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
        email = body.get('email', '').strip().lower()
    except Exception:
        email = request.POST.get('email', '').strip().lower()

    if not email:
        return JsonResponse({'status': 'error', 'message': 'Email is required.'}, status=400)

    # Validate it looks like an email
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'status': 'error', 'message': 'Enter a valid email address.'}, status=400)

    # Block already-registered emails
    if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
        return JsonResponse({'status': 'error', 'message': 'This email is already registered. Please login instead.'}, status=400)

    # Generate OTP
    code = str(random.randint(100000, 999999))
    SignupOTP.objects.filter(email__iexact=email).delete()
    SignupOTP.objects.create(email=email, code=code)

    # Send email
    try:
        send_mail(
            subject='Your NPITS Registration Code',
            message=(
                f'Your 6-digit verification code is: {code}\n\n'
                f'This code is valid for 10 minutes.\n\n'
                f'If you did not request this, please ignore this email.'
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': f'Failed to send email: {type(e).__name__}. Please try again.'}, status=500)

    return JsonResponse({'status': 'ok', 'message': f'OTP sent to {email}'})


@csrf_exempt
def verify_signup_otp(request):
    """AJAX endpoint: verifies OTP entered during signup. Sets session flag on success."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
        email = body.get('email', '').strip().lower()
        code = body.get('otp', '').strip()
    except Exception:
        email = request.POST.get('email', '').strip().lower()
        code = request.POST.get('otp', '').strip()

    if not email or not code:
        return JsonResponse({'status': 'error', 'message': 'Email and OTP are required.'}, status=400)

    otp_obj = SignupOTP.objects.filter(email__iexact=email, code=code).first()
    if not otp_obj:
        return JsonResponse({'status': 'error', 'message': 'Invalid OTP. Please check and try again.'}, status=400)
    if not otp_obj.is_valid():
        otp_obj.delete()
        return JsonResponse({'status': 'error', 'message': 'OTP has expired. Please request a new one.'}, status=400)

    # Mark in session
    request.session['signup_otp_verified'] = True
    request.session['signup_verified_email'] = email
    return JsonResponse({'status': 'ok', 'message': 'Email verified successfully!'})


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            post_email = form.cleaned_data.get('email', '').strip().lower()

            # Gate: OTP must be verified in session
            otp_verified = request.session.get('signup_otp_verified')
            verified_email = request.session.get('signup_verified_email', '').strip().lower()

            if not otp_verified or verified_email != post_email:
                messages.error(request, 'Please verify your email with the OTP before signing up.')
                return render(request, 'registration/register.html', {'form': form})

            user = form.save()

            # Clean up session flags and OTP record
            request.session.pop('signup_otp_verified', None)
            request.session.pop('signup_verified_email', None)
            SignupOTP.objects.filter(email__iexact=post_email).delete()

            login(request, user, backend='core.backends.EmailOrMobileBackend')

            # Send Welcome Email
            try:
                send_mail(
                    subject='Welcome to NPITS',
                    message=f'Hi {user.email},\n\nWelcome to Net Profit Investment Tracking System. Thank you for registering with us.\n\nBest Regards,\nNPITS Team',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, "Registration successful. Welcome email sent.")
            except Exception as e:
                print(f"Error sending email: {e}")
                messages.success(request, "Registration successful, but failed to send welcome email.")

            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def edit_portfolio_item(request, pk):
    item = get_object_or_404(Portfolio, pk=pk, user=request.user)
    if request.method == 'POST':
        form = PortfolioForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated {item.instrument.symbol} successfully.")
            return redirect('dashboard')
    else:
        form = PortfolioForm(instance=item)
    return render(request, 'core/edit_portfolio.html', {'form': form, 'item': item})

@login_required
def delete_portfolio_item(request, pk):
    item = get_object_or_404(Portfolio, pk=pk, user=request.user)
    symbol = item.instrument.symbol
    if request.method == 'POST':
        item.delete()
        messages.success(request, f"Deleted {symbol} from portfolio.")
        return redirect('dashboard')
    return render(request, 'core/delete_confirm.html', {'item': item})

@login_required
def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('dashboard')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'core/edit_profile.html', {'form': form})


@login_required
@csrf_exempt
def buy_stock(request):
    if request.method == 'POST':
        symbol = request.POST.get('symbol', '').strip().upper()
        quantity_str = request.POST.get('quantity', '0')
        price_str = request.POST.get('price', '0')
        
        try:
            quantity = int(quantity_str)
            price = Decimal(price_str)
        except (ValueError, TypeError):
            messages.error(request, "Invalid quantity or price.")
            return redirect('dashboard')
        date_str = request.POST.get('date')
        
        transaction_date = pd.to_datetime(date_str).date() if date_str else timezone.now().date()
        
        try:
            inst = Instrument.objects.get(symbol__iexact=symbol, is_verified=True)
        except Instrument.DoesNotExist:
            # Fallback for manual addition if not found or not verified
            inst, _ = Instrument.objects.get_or_create(symbol=symbol, defaults={'name': symbol, 'is_verified': True})
        
        # Create Transaction record
        Transaction.objects.create(
            user=request.user,
            instrument=inst,
            transaction_type='BUY',
            quantity=quantity,
            remaining_quantity=quantity,
            price=price,
            date=transaction_date
        )
        
        portfolio, created = Portfolio.objects.get_or_create(
            user=request.user, 
            instrument=inst,
            defaults={'quantity': 0, 'avg_cost': Decimal('0'), 'ltp': price}
        )
        
        # Update Weighted Average Cost for Portfolio summary
        current_total_cost = Decimal(str(portfolio.quantity)) * portfolio.avg_cost
        new_total_cost = Decimal(str(quantity)) * price
        total_quantity = portfolio.quantity + quantity
        
        new_avg_cost = (current_total_cost + new_total_cost) / Decimal(str(total_quantity))
        
        portfolio.quantity = total_quantity
        portfolio.avg_cost = new_avg_cost
        # Only update LTP if it was 0 or just created
        if created or not portfolio.ltp or portfolio.ltp == 0:
            portfolio.ltp = price
        portfolio.save()
        
        messages.success(request, f"Bought {quantity} units of {symbol} at {price}")
        return redirect('dashboard')
    return redirect('dashboard')

@login_required
@csrf_exempt
def sell_stock(request):
    if request.method == 'POST':
        symbol = request.POST.get('symbol').strip().upper()
        quantity_to_sell = int(request.POST.get('quantity'))
        price = Decimal(request.POST.get('price'))
        exit_date_str = request.POST.get('exit_date')
        exit_date = pd.to_datetime(exit_date_str).date() if exit_date_str else timezone.now().date()
        
        inst = get_object_or_404(Instrument, symbol__iexact=symbol, is_verified=True)
        portfolio = get_object_or_404(Portfolio, user=request.user, instrument=inst)
        
        if quantity_to_sell > portfolio.quantity:
            messages.error(request, f"Insufficient quantity to sell. You have {portfolio.quantity} units.")
            return redirect('dashboard')
            
        # 1. Intraday Logic: Check for a matching BUY today with same volume
        intraday_buy = Transaction.objects.filter(
            user=request.user,
            instrument=inst,
            transaction_type='BUY',
            date=exit_date,
            quantity=quantity_to_sell,
            remaining_quantity=quantity_to_sell
        ).first()

        total_buy_value = Decimal('0')
        remaining_to_deduct = quantity_to_sell
        first_entry_date = None

        if intraday_buy:
            total_buy_value = Decimal(str(quantity_to_sell)) * intraday_buy.price
            first_entry_date = intraday_buy.date
            intraday_buy.remaining_quantity = 0
            intraday_buy.save()
            remaining_to_deduct = 0
        else:
            # 2. FIFO Logic: Fetch active buy transactions
            buy_txs = Transaction.objects.filter(
                user=request.user,
                instrument=inst,
                transaction_type='BUY',
                remaining_quantity__gt=0
            ).order_by('date', 'created_at')
            
            for tx in buy_txs:
                if remaining_to_deduct <= 0:
                    break
                
                if first_entry_date is None:
                    first_entry_date = tx.date
                    
                deduct = min(tx.remaining_quantity, remaining_to_deduct)
                total_buy_value += Decimal(str(deduct)) * tx.price
                tx.remaining_quantity -= deduct
                tx.save()
                remaining_to_deduct -= deduct
            
        sell_value = Decimal(str(quantity_to_sell)) * price
        profit = sell_value - total_buy_value
        
        # Record Sell Transaction
        Transaction.objects.create(
            user=request.user,
            instrument=inst,
            transaction_type='SELL',
            quantity=quantity_to_sell,
            price=price,
            date=exit_date
        )
        
        # Record in PnLStatement
        PnLStatement.objects.create(
            user=request.user,
            instrument=inst,
            entry_date=first_entry_date,
            quantity=quantity_to_sell,
            buy_value=total_buy_value,
            sell_value=sell_value,
            realized_profit=profit,
            exit_date=exit_date
        )
        
        # Update Portfolio
        portfolio.quantity -= quantity_to_sell
        if portfolio.quantity <= 0:
            portfolio.delete()
        else:
            # Recalculate average cost based on remaining lots
            remaining_lots = Transaction.objects.filter(
                user=request.user,
                instrument=inst,
                transaction_type='BUY',
                remaining_quantity__gt=0
            )
            if remaining_lots.exists():
                total_qty = sum(l.remaining_quantity for l in remaining_lots)
                total_cost = sum(Decimal(str(l.remaining_quantity)) * l.price for l in remaining_lots)
                portfolio.avg_cost = total_cost / Decimal(str(total_qty))
            
            # Save the updated quantity and (potentially) avg_cost
            portfolio.save()
            
        messages.success(request, f"Sold {quantity_to_sell} units of {symbol} at {price}. Profit: {profit}")
        return redirect('dashboard')
def get_current_financial_year():
    now = timezone.now().date()
    # Standard Indian Financial Year starts April 1.
    # User requested transition to 2026-2027 starting March 27, 2026.
    if now.month >= 4 or (now.year == 2026 and now.month == 3 and now.day >= 27):
        return f"{now.year}-{now.year+1}"
    else:
        return f"{now.year-1}-{now.year}"

@login_required
def transaction_history(request):
    """View all buy/sell transactions for the user."""
    transactions = Transaction.objects.filter(user=request.user).select_related('instrument').order_by('-date', '-created_at')
    
    current_fy_str = get_current_financial_year()
    portfolios = Portfolio.objects.filter(user=request.user)
    current_invested = sum(p.invested_amount for p in portfolios)
    current_value = sum(p.current_value for p in portfolios)
    current_unrealized = sum(p.unrealized_pnl for p in portfolios)
    
    start_year = int(current_fy_str.split('-')[0])
    end_year = int(current_fy_str.split('-')[1])
    from .models import FinancialYearData
    
    total_realized_profits = PnLStatement.objects.filter(user=request.user)
    total_realized = sum(rp.realized_profit for rp in total_realized_profits)
    
    past_fys = FinancialYearData.objects.filter(user=request.user).exclude(financial_year=current_fy_str)
    past_fys_realized_sum = sum(fd.realized_profit for fd in past_fys)
    
    current_realized = total_realized - past_fys_realized_sum
    
    # Automatically add/update current FY
    current_fy_obj, _ = FinancialYearData.objects.update_or_create(
        user=request.user,
        financial_year=current_fy_str,
        defaults={
            'invested_amount': current_invested,
            'current_value': current_value,
            'unrealized_pnl': current_unrealized,
            'realized_profit': current_realized
        }
    )
    
    # Get all FY data (including current that we just saved/updated) ordered by most recent
    fy_data = FinancialYearData.objects.filter(user=request.user).order_by('-financial_year')
    current_fy_data = [fd for fd in fy_data if fd.financial_year == current_fy_str]
    past_fy_data = [fd for fd in fy_data if fd.financial_year != current_fy_str]
    
    return render(request, 'core/transactions.html', {
        'transactions': transactions,
        'current_fy_data': current_fy_data[0] if current_fy_data else None,
        'past_fy_data': past_fy_data
    })

@login_required
@csrf_exempt
def save_fy_data(request):
    if request.method == 'POST':
        import json
        from decimal import Decimal
        try:
            data = json.loads(request.body)
            from .models import FinancialYearData
            for row in data:
                fy = row.get('year')
                if fy:
                    obj = FinancialYearData.objects.filter(user=request.user, financial_year=fy).first()
                    invested = Decimal(str(row.get('invested', 0)))
                    current = Decimal(str(row.get('current', 0)))
                    unrealized = Decimal(str(row.get('unrealized', 0)))
                    realized = Decimal(str(row.get('realized', 0)))
                    
                    if obj:
                        if obj.is_locked: 
                            continue # Locked, silently ignore
                        
                        # Only update if data actually changed
                        if (obj.invested_amount != invested or 
                            obj.current_value != current or 
                            obj.unrealized_pnl != unrealized or 
                            obj.realized_profit != realized):
                            
                            obj.invested_amount = invested
                            obj.current_value = current
                            obj.unrealized_pnl = unrealized
                            obj.realized_profit = realized
                            obj.save()
                    else:
                        FinancialYearData.objects.create(
                            user=request.user,
                            financial_year=fy,
                            invested_amount=invested,
                            current_value=current,
                            unrealized_pnl=unrealized,
                            realized_profit=realized,
                            edit_count=1
                        )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=405)

@login_required
@csrf_exempt
def toggle_fy_lock(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            fy = data.get('year')
            from .models import FinancialYearData
            obj = get_object_or_404(FinancialYearData, user=request.user, financial_year=fy)
            obj.is_locked = not obj.is_locked
            obj.save()
            return JsonResponse({'status': 'success', 'is_locked': obj.is_locked})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=405)

@login_required
@csrf_exempt
def delete_fy_data(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            fy = data.get('year')
            from .models import FinancialYearData
            obj = get_object_or_404(FinancialYearData, user=request.user, financial_year=fy)
            if obj.is_locked:
                return JsonResponse({'status': 'error', 'message': 'Cannot delete a locked record.'}, status=403)
            obj.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=405)

@login_required
def lot_breakdown(request, instrument_id):
    """View specific buy lots for a particular instrument."""
    inst = get_object_or_404(Instrument, id=instrument_id)
    lots = Transaction.objects.filter(
        user=request.user,
        instrument=inst,
        transaction_type='BUY',
        remaining_quantity__gt=0
    ).order_by('date', 'created_at')
    
    # Enrich lots with days held and unrealized P&L
    live_ltps = fetch_live_ltp()
    ltp = Decimal(str(live_ltps.get(inst.symbol.upper(), 0))) or Decimal('0')
    
    enriched_lots = []
    for lot in lots:
        days_held = (timezone.now().date() - lot.date).days
        current_value = Decimal(str(lot.remaining_quantity)) * ltp
        buy_value = Decimal(str(lot.remaining_quantity)) * lot.price
        pnl = current_value - buy_value
        pnl_pct = (pnl / buy_value * 100) if buy_value else 0
        
        enriched_lots.append({
            'id': lot.id,
            'date': lot.date,
            'quantity': lot.remaining_quantity,
            'price': lot.price,
            'days_held': days_held,
            'ltp': ltp,
            'unrealized_pnl': pnl,
            'pnl_pct': pnl_pct
        })
        
    total_quantity = sum(l['quantity'] for l in enriched_lots)
    total_invested = sum(Decimal(str(l['quantity'])) * l['price'] for l in enriched_lots)
    avg_cost = total_invested / Decimal(str(total_quantity)) if total_quantity > 0 else 0
    
    context = {
        'instrument': inst,
        'lots': enriched_lots,
        'total_quantity': total_quantity,
        'total_invested': total_invested,
        'avg_cost': avg_cost,
    }
    return render(request, 'core/lot_breakdown.html', context)

@login_required
def edit_lot(request, pk):
    """Edit an individual purchase lot."""
    lot = get_object_or_404(Transaction, pk=pk, user=request.user, transaction_type='BUY')
    
    if request.method == 'POST':
        try:
            new_qty = int(request.POST.get('quantity'))
            new_price = Decimal(request.POST.get('price'))
            new_date = pd.to_datetime(request.POST.get('date')).date()
            
            # Difference in quantity
            qty_diff = new_qty - lot.remaining_quantity
            
            lot.quantity = new_qty
            lot.remaining_quantity = new_qty
            lot.price = new_price
            lot.date = new_date
            lot.save()
            
            # Update Portfolio
            portfolio = Portfolio.objects.get(user=request.user, instrument=lot.instrument)
            portfolio.quantity += qty_diff
            
            # Recalculate average cost
            all_lots = Transaction.objects.filter(
                user=request.user, 
                instrument=lot.instrument, 
                transaction_type='BUY', 
                remaining_quantity__gt=0
            )
            total_qty = sum(l.remaining_quantity for l in all_lots)
            total_cost = sum(Decimal(str(l.remaining_quantity)) * l.price for l in all_lots)
            portfolio.avg_cost = total_cost / Decimal(str(total_qty)) if total_qty > 0 else 0
            
            if portfolio.quantity <= 0:
                portfolio.delete()
            else:
                portfolio.save()
                
            messages.success(request, f"Lot for {lot.instrument.symbol} updated successfully.")
            return redirect('lot_breakdown', instrument_id=lot.instrument.id)
        except Exception as e:
            messages.error(request, f"Error updating lot: {e}")
            
    return render(request, 'core/edit_lot.html', {'lot': lot, 'form': EditLotForm(initial={
        'quantity': lot.remaining_quantity,
        'price': lot.price,
        'date': lot.date
    })})

@login_required
def delete_lot(request, pk):
    """Delete an individual purchase lot."""
    lot = get_object_or_404(Transaction, pk=pk, user=request.user, transaction_type='BUY')
    instrument = lot.instrument
    instrument_id = instrument.id
    
    # Update Portfolio before deleting
    try:
        portfolio = Portfolio.objects.get(user=request.user, instrument=instrument)
        portfolio.quantity -= lot.remaining_quantity
        
        lot.delete()
        
        # Recalculate average cost
        remaining_lots = Transaction.objects.filter(
            user=request.user, 
            instrument=instrument, 
            transaction_type='BUY', 
            remaining_quantity__gt=0
        )
        
        if not remaining_lots.exists():
            portfolio.delete()
        else:
            total_qty = sum(l.remaining_quantity for l in remaining_lots)
            total_cost = sum(Decimal(str(l.remaining_quantity)) * l.price for l in remaining_lots)
            portfolio.avg_cost = total_cost / Decimal(str(total_qty))
            portfolio.save()
            
        messages.success(request, f"Lot deleted successfully.")
    except Portfolio.DoesNotExist:
        lot.delete()
        messages.success(request, f"Lot deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting lot: {e}")
        
    return redirect('lot_breakdown', instrument_id=instrument_id)
@csrf_exempt
def sync_data_api(request):
    """API endpoint to trigger data synchronization with rate limiting via cache."""
    sync_key = 'last_sync_timestamp'
    lock_key = 'sync_in_progress'
    
    # Rate limit: 1 minute
    last_sync = cache.get(sync_key)
    now = timezone.now().timestamp()
    
    if last_sync is not None and (now - last_sync) < 60:
        return JsonResponse({'status': 'skipped', 'message': 'Recently synced'})
    
    if cache.get(lock_key):
        return JsonResponse({'status': 'skipped', 'message': 'Sync in progress'})
    
    # Set lock and timestamp
    cache.set(lock_key, True, 300) # 5 min safety lock
    cache.set(sync_key, now, 3600)
    
    try:
        perform_sync()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    finally:
        cache.delete(lock_key)

def assetlinks_json(request):
    """
    Serve the Digital Asset Links file for Android TWA verification.
    """
    asset_links = [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "in.npits.twa",
                "sha256_cert_fingerprints": [
                    "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00"
                ]
            }
        }
    ]
    return JsonResponse(asset_links, safe=False)

@csrf_exempt
def index_data_api(request):
    """Fetch historical OHLC data for indices, commodities, and global markets."""
    symbol = request.GET.get('symbol', '^NSEI')
    name = request.GET.get('name', '')
    period = request.GET.get('period', '1d')
    
    # Mapping for common intervals
    interval_map = {
        '1d': '5m',
        '1mo': '1d',
        '6mo': '1d',
        '9mo': '1d',
        '1y': '1d',
        'max': '1wk'
    }
    interval = interval_map.get(period, '1d')

    try:
        cache_key = f'index_data_{symbol}_{period}'
        data = cache.get(cache_key)
        if data:
            return JsonResponse(data)

        ticker = yf.Ticker(symbol)
        # For 1d, sometimes data is delayed or empty on weekends. Try 5d if 1d fails.
        hist = ticker.history(period=period, interval=interval)
        
        # Drop rows with NaN Close values (e.g. incomplete current week for futures)
        hist = hist.dropna(subset=['Close'])
        
        if hist.empty and period == '1d':
            hist = ticker.history(period='5d', interval='5m')
            hist = hist.dropna(subset=['Close'])
            
        if hist.empty:
            return JsonResponse({'status': 'error', 'message': f'No data found for {symbol}'}, status=404)

        # Prepare data for Chart.js
        if period == '1d':
            # For 1d, only show today's data or the last available day's data
            last_date = hist.index[-1].date()
            day_data = hist[hist.index.date == last_date]
            if day_data.empty: day_data = hist.tail(50) # Fallback
            labels = [d.strftime('%H:%M') for d in day_data.index]
            prices = [round(float(p), 2) for p in day_data['Close']]
        elif period == 'max':
            labels = [d.strftime('%Y') for d in hist.index]
            prices = [round(float(p), 2) for p in hist['Close']]
        else:
            labels = [d.strftime('%Y-%m-%d') for d in hist.index]
            prices = [round(float(p), 2) for p in hist['Close']]
            
        # Calculate change info based on the fetched history
        current_price = prices[-1]

        if period == '1d':
            # Proper 1-day change: relative to previous day's close
            info = ticker.info
            prev_price = info.get('regularMarketPreviousClose') or info.get('previousClose')
            
            if not prev_price:
                # period='1d' is currently intraday 5m data.
                # Fetch daily data to get yesterday's close.
                hist_daily = ticker.history(period='5d', interval='1d')
                if len(hist_daily) >= 2:
                    prev_price = float(hist_daily['Close'].iloc[-2])
                else:
                    prev_price = prices[0] # Fallback to open
        else:
            prev_price = prices[0]

        change = round(current_price - prev_price, 2)
        change_pct = round((change / prev_price) * 100, 2) if prev_price else 0

        # Heuristic for display name if not provided
        if not name:
            if '^NSEI' in symbol: name = 'NIFTY 50'
            elif '^BSESN' in symbol: name = 'SENSEX'
            elif '^IXIC' in symbol: name = 'NASDAQ'
            elif '^DJI' in symbol: name = 'DOW JONES'
            else: name = symbol

        result = {
            'labels': labels,
            'prices': prices,
            'current_price': current_price,
            'previous_close': prev_price,
            'change': change,
            'change_pct': change_pct,
            'symbol_name': name,
            'symbol': symbol,
            'period': period
        }
        
        cache.set(cache_key, result, 300) # 5 mins
        return JsonResponse(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def stock_price_api(request):
    """Fetch live price and basic info for any stock symbol."""
    symbol = request.GET.get('symbol', '').strip().upper()
    if not symbol:
        return JsonResponse({'status': 'error', 'message': 'Symbol is required'}, status=400)

    # Smart symbol handling: don't append .NS to indices, commodities, or already suffixed symbols
    if any(x in symbol for x in ['^', '.', '=F']):
        symbol_ns = symbol
    else:
        symbol_ns = f"{symbol}.NS"

    try:
        cache_key = f'stock_price_{symbol_ns}'
        data = cache.get(cache_key)
        if data:
            return JsonResponse(data)

        ticker = yf.Ticker(symbol_ns)
        hist = ticker.history(period='5d') # Get 5 days to be safe with weekends
        
        if hist.empty:
            if symbol_ns.endswith('.NS'):
                symbol_ns = f"{symbol}.BO"
                ticker = yf.Ticker(symbol_ns)
                hist = ticker.history(period='5d')
                if hist.empty:
                    return JsonResponse({'status': 'error', 'message': 'Stock not found'}, status=404)
            else:
                return JsonResponse({'status': 'error', 'message': 'Stock not found'}, status=404)

        info = ticker.info
        current_price = round(float(hist['Close'].iloc[-1]), 2)
        
        # Prioritize info previousClose for accuracy
        prev_close = info.get('regularMarketPreviousClose') or info.get('previousClose')
        if not prev_close:
            prev_close = round(float(hist['Close'].iloc[-2]), 2) if len(hist) > 1 else current_price
        
        change = round(current_price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

        result = {
            'symbol': symbol_ns,
            'name': info.get('longName', symbol),
            'price': current_price,
            'previous_close': prev_close,
            'change': change,
            'change_pct': change_pct,
            'currency': info.get('currency', 'INR'),
            'market': info.get('market', 'in_market'),
            'pe': info.get('trailingPE'),
            'volume': info.get('volume'),
            'avg_volume': info.get('averageVolume'),
            'eps': info.get('trailingEps'),
            'high52': info.get('fiftyTwoWeekHigh'),
            'low52': info.get('fiftyTwoWeekLow'),
            'market_cap': info.get('marketCap'),
            'dividend': info.get('dividendYield')
        }
        
        cache.set(cache_key, result, 60) # 1 min cache for live prices
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def stock_suggestions_api(request):
    """Provide real-time suggestions based on symbol or name from our DB."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'status': 'success', 'results': []})

    from core.models import Instrument
    results = Instrument.objects.filter(
        models.Q(symbol__icontains=q) | models.Q(name__icontains=q),
        is_verified=True
    ).values('symbol', 'name')[:10]

    return JsonResponse({'status': 'success', 'results': list(results)})

@csrf_exempt
def stock_history_api(request):
    """Fetch historical OHLC data for any stock symbol."""
    symbol = request.GET.get('symbol', '').strip().upper()
    period = request.GET.get('period', '1d')
    
    if not symbol:
        return JsonResponse({'status': 'error', 'message': 'Symbol is required'}, status=400)

    # Smart symbol handling: append .NS if no suffix
    if not any(x in symbol for x in ['^', '.', '=F']):
        symbol_ns = f"{symbol}.NS"
    else:
        symbol_ns = symbol

    # Mapping for common intervals
    interval_map = {
        '1d': '5m',
        '1mo': '1d',
        '6mo': '1d',
        '9mo': '1d',
        '1y': '1d',
        'max': '1wk'
    }
    interval = interval_map.get(period, '1d')

    try:
        cache_key = f'stock_history_{symbol_ns}_{period}'
        data = cache.get(cache_key)
        if data:
            return JsonResponse(data)

        ticker = yf.Ticker(symbol_ns)
        hist = ticker.history(period=period, interval=interval)
        
        hist = hist.dropna(subset=['Close'])
        
        if hist.empty and period == '1d':
            hist = ticker.history(period='5d', interval='5m')
            hist = hist.dropna(subset=['Close'])
            
        if hist.empty:
            if symbol_ns.endswith('.NS'):
                symbol_ns = symbol_ns.replace('.NS', '.BO')
                ticker = yf.Ticker(symbol_ns)
                hist = ticker.history(period=period, interval=interval)
                hist = hist.dropna(subset=['Close'])
                if hist.empty and period == '1d':
                    hist = ticker.history(period='5d', interval='5m')
                    hist = hist.dropna(subset=['Close'])

        if hist.empty:
            return JsonResponse({'status': 'error', 'message': f'No history found for {symbol_ns}'}, status=404)

        # Prepare data for Chart.js
        if period == '1d':
            last_date = hist.index[-1].date()
            day_data = hist[hist.index.date == last_date]
            if day_data.empty: day_data = hist.tail(50)
            labels = [d.strftime('%H:%M') for d in day_data.index]
            prices = [round(float(p), 2) for p in day_data['Close']]
        elif period == 'max':
            labels = [d.strftime('%Y') for d in hist.index]
            prices = [round(float(p), 2) for p in hist['Close']]
        else:
            labels = [d.strftime('%Y-%m-%d') for d in hist.index]
            prices = [round(float(p), 2) for p in hist['Close']]
            
        current_price = prices[-1]

        if period == '1d':
            # Use ticker.info for accurate baseline
            info = ticker.info
            prev_price = info.get('regularMarketPreviousClose') or info.get('previousClose')

            if not prev_price:
                hist_daily = ticker.history(period='5d', interval='1d')
                if len(hist_daily) >= 2:
                    prev_price = float(hist_daily['Close'].iloc[-2])
                else:
                    prev_price = prices[0]
        else:
            prev_price = prices[0]

        change = round(current_price - prev_price, 2)
        change_pct = round((change / prev_price) * 100, 2) if prev_price else 0

        result = {
            'labels': labels,
            'prices': prices,
            'current_price': current_price,
            'previous_close': prev_price,
            'change': change,
            'change_pct': change_pct,
            'symbol': symbol_ns,
            'period': period
        }
        
        cache.set(cache_key, result, 300)
        return JsonResponse(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def watchlist(request):
    """View to display the user's personal watchlist."""
    from core.models import Watchlist, Portfolio
    from .utils import fetch_live_ltp
    
    watchlist_items = Watchlist.objects.filter(user=request.user).select_related('instrument')
    # Get portfolio data to support actions
    portfolio_data = {p.instrument_id: {'qty': p.quantity, 'invested': float(p.invested_amount or 0)} 
                      for p in Portfolio.objects.filter(user=request.user)}
    
    live_ltps = fetch_live_ltp() or {}
    results = []
    for item in watchlist_items:
        inst = item.instrument
        if not inst:
            continue
            
        ltp = float(live_ltps.get(inst.symbol.upper(), 0))
        if ltp <= 0:
            ltp = float(inst.last_price or 0)
            
        change = float(inst.price_change or 0)
        prev_close = ltp - change
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        
        p_data = portfolio_data.get(inst.id, {'qty': 0, 'invested': 0})
        
        results.append({
            'symbol': inst.symbol,
            'name': inst.name,
            'ltp': ltp,
            'change': change,
            'change_pct': change_pct,
            'notes': item.notes,
            'added_at': item.added_at,
            'instrument_id': inst.id,
            'portfolio_qty': p_data['qty'],
            'invested_amount': p_data['invested']
        })
        
    return render(request, 'core/watchlist.html', {'watchlist': results})

@csrf_exempt
@login_required
def add_to_watchlist_api(request):
    """API to add a symbol to the user's watchlist."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    
    symbol = request.POST.get('symbol', '').strip().upper()
    if not symbol:
        return JsonResponse({'status': 'error', 'message': 'Symbol is required'}, status=400)
    
    from .models import Instrument, Watchlist
    import yfinance as yf
    
    # Try to find the instrument
    instrument = Instrument.objects.filter(symbol__iexact=symbol).first()
    
    if not instrument:
        # Try to find exactly as provided or with .NS
        search_symbol = symbol if '.' in symbol else f"{symbol}.NS"
        try:
            ticker = yf.Ticker(search_symbol)
            info = ticker.info
            if info and 'symbol' in info and info.get('symbol'):
                fetched_symbol = str(info.get('symbol')).upper()
                instrument, _ = Instrument.objects.get_or_create(
                    symbol=fetched_symbol,
                    defaults={
                        'name': info.get('longName') or info.get('shortName') or symbol,
                        'last_price': info.get('regularMarketPrice') or info.get('previousClose') or 0,
                        'is_verified': True
                    }
                )
            else:
                return JsonResponse({'status': 'error', 'message': f'Symbol {symbol} not found in market'}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc() # Log to server console
            return JsonResponse({'status': 'error', 'message': f'Error fetching symbol: {str(e)}'}, status=500)

    try:
        Watchlist.objects.get_or_create(user=request.user, instrument=instrument)
        return JsonResponse({'status': 'success', 'message': f'{symbol} added to watchlist'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': f'Error saving to watchlist: {str(e)}'}, status=500)

@csrf_exempt
@login_required
def remove_from_watchlist_api(request):
    """API to remove a symbol from the user's watchlist."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    
    symbol = request.POST.get('symbol', '').strip().upper()
    if not symbol:
        return JsonResponse({'status': 'error', 'message': 'Symbol is required'}, status=400)
    
    from core.models import Instrument, Watchlist
    instrument = Instrument.objects.filter(symbol__iexact=symbol).first()
    
    if instrument:
        Watchlist.objects.filter(user=request.user, instrument=instrument).delete()
        return JsonResponse({'status': 'success', 'message': f'{symbol} removed from watchlist'})
    
    return JsonResponse({'status': 'error', 'message': 'Instrument not found'}, status=404)
