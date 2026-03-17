import pandas as pd
import requests
import io
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

from django.utils import timezone
import threading
from django import db
import math
from decimal import Decimal
from django.db.models import Sum, Max
from django.db.models.functions import Upper
from django.db import transaction
from core.models import Instrument

def resolve_instrument(symbol_or_name):
    """
    Tries to resolve an Instrument object from a symbol or name.
    1. Exact symbol match
    2. Exact name match
    3. Symbol match without common suffixes (-GB, -BE, -EQ, etc.)
    """
    if not symbol_or_name:
        return None
        
    clean_val = str(symbol_or_name).strip().upper()
    
    # 1. Exact Symbol Match
    inst = Instrument.objects.filter(symbol__iexact=clean_val, is_verified=True).first()
    if inst:
        return inst
        
    # 2. Exact Name Match
    inst = Instrument.objects.filter(name__iexact=clean_val, is_verified=True).first()
    if inst:
        return inst
        
    # 3. Handle suffixes (e.g., SGBMAR31IV-GB -> SGBMAR31IV)
    # Common suffixes in Indian markets
    suffixes = ['-GB', '-BE', '-EQ', '.NS', '.BO']
    for suffix in suffixes:
        if clean_val.endswith(suffix):
            base = clean_val[:-len(suffix)]
            inst = Instrument.objects.filter(symbol__iexact=base, is_verified=True).first()
            if inst:
                return inst
            inst = Instrument.objects.filter(name__iexact=base, is_verified=True).first()
            if inst:
                return inst
                
    return None

def perform_sync():
    """Execute the synchronization logic for market tickers and instruments."""
    from core.models import MarketTicker, Instrument, Portfolio
    logger.info("Starting background sync process...")
    
    # 1. Sync Market Ticker Data
    market_url = "https://docs.google.com/spreadsheets/d/12eLJHTlHO1naQgJ-dzf-UTgUbasVv02tgwlHKofG2Y4/gviz/tq?tqx=out:csv&sheet=market"
    try:
        response = requests.get(market_url, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        
        seen_tickers = set()
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    name = str(row.iloc[0]).strip()
                    price_val = row.iloc[1]
                    change = row.iloc[2] if len(row) > 2 else 0
                    
                    if pd.notna(name) and pd.notna(price_val):
                        if isinstance(price_val, str) and price_val.lower() == 'nan':
                            continue
                        try:
                            price = float(price_val)
                            if math.isnan(price):
                                continue
                                
                            try:
                                if isinstance(change, str) and change.lower() == 'nan':
                                    change_val = 0
                                else:
                                    change_val = float(change)
                                    if math.isnan(change_val):
                                        change_val = 0
                            except (ValueError, TypeError):
                                change_val = 0
                            
                            MarketTicker.objects.update_or_create(
                                name=name,
                                defaults={'price': price, 'change': change_val}
                            )
                            seen_tickers.add(name)
                        except (ValueError, TypeError):
                            continue
                except Exception as e:
                    logger.error(f"Error processing market ticker row: {e}")
        
        # Delete tickers not in the current sheet
        if seen_tickers:
            deleted_count, _ = MarketTicker.objects.exclude(name__in=seen_tickers).delete()
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} stale market tickers.")
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")

    # 2. Sync Instrument LTP Data
    ltp_url = "https://docs.google.com/spreadsheets/d/12eLJHTlHO1naQgJ-dzf-UTgUbasVv02tgwlHKofG2Y4/export?format=csv"
    try:
        response = requests.get(ltp_url, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text), skiprows=1)
        
        ltp_map = {}
        for _, row in df.iterrows():
            try:
                symbol_val = row.iloc[2]
                if pd.isna(symbol_val): continue
                symbol = str(symbol_val).strip().upper()
                if not symbol or symbol == 'NAN': continue
                
                ltp_val = row.iloc[4]
                if pd.isna(ltp_val): continue
                try:
                    ltp = float(ltp_val)
                    if math.isnan(ltp): continue
                except (ValueError, TypeError):
                    continue
                
                change_val = 0
                if len(row) > 5:
                    try:
                        cv = row.iloc[5]
                        if pd.notna(cv):
                            change_val = float(cv)
                            if math.isnan(change_val):
                                change_val = 0
                    except (ValueError, TypeError):
                        pass

                pe_val = None
                if len(row) > 8:
                    try:
                        pv = row.iloc[8]
                        if pd.notna(pv):
                            pe_val = float(pv)
                    except (ValueError, TypeError):
                        pass
                
                lh_diff_val = None
                if len(row) > 9:
                    try:
                        lv = row.iloc[9]
                        if pd.notna(lv):
                            lh_diff_val = float(lv)
                    except (ValueError, TypeError):
                        pass

                if ltp > 0:
                    ltp_map[symbol] = (ltp, change_val, pe_val, lh_diff_val)
            except (ValueError, TypeError, IndexError):
                continue
        
        if ltp_map:
            with transaction.atomic():
                # Update Instruments
                instruments = Instrument.objects.filter(symbol__in=ltp_map.keys())
                for inst in instruments:
                    ltp, change, pe, lh_diff = ltp_map[inst.symbol]
                    inst.last_price = ltp
                    inst.price_change = change
                    inst.pe_ratio = pe
                    inst.diff_from_lh_pct = lh_diff
                    inst.last_updated = timezone.now()
                    inst.save(update_fields=['last_price', 'price_change', 'pe_ratio', 'diff_from_lh_pct', 'last_updated'])
                
                # Update Portfolios
                portfolios = Portfolio.objects.all().select_related('instrument')
                for p in portfolios:
                    symbol = p.instrument.symbol.upper()
                    if symbol in ltp_map:
                        ltp = ltp_map[symbol][0]
                        if float(p.ltp) != float(ltp):
                            p.ltp = ltp
                            p.save(update_fields=['ltp'])
    except Exception as e:
        logger.error(f"Error fetching instrument data: {e}")
    except Exception as e:
        logger.error(f"Error fetching instrument data: {e}")

    # 3. Sync Strategy Stocks
    STRATEGY_SHEET_TABS = {
        'flexi': ('FlexiMultiInvest', 'Flexi Multi Invest'),
        'quant': ('NiftyQuant', 'Nifty Quant'),
        'pyramid': ('Pyramiding', 'Pyramiding'),
        'growth': ('ReinvestX', 'Reinvest X'),
    }
    SHEET_ID = "12eLJHTlHO1naQgJ-dzf-UTgUbasVv02tgwlHKofG2Y4"
    
    from core.models import Strategy, StrategyStock
    for strategy_key, (tab_name, display_name) in STRATEGY_SHEET_TABS.items():
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={tab_name}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            strategy, _ = Strategy.objects.get_or_create(
                name=strategy_key,
                defaults={'display_name': display_name}
            )
            
            # Clear existing stocks for this strategy
            StrategyStock.objects.filter(strategy=strategy).delete()
            
            stocks_to_create = []
            order = 0
            for line in response.text.splitlines():
                parts = line.split(',')
                if not parts: continue
                symbol = parts[0].strip().strip('"').strip().upper()
                if symbol and symbol != 'NAN' and symbol != 'SYMBOL':
                    stocks_to_create.append(StrategyStock(
                        strategy=strategy,
                        symbol=symbol,
                        order=order
                    ))
                    order += 1
            
            if stocks_to_create:
                StrategyStock.objects.bulk_create(stocks_to_create)
                logger.info(f"Synced {len(stocks_to_create)} stocks for strategy: {strategy_key}")
                
        except Exception as e:
            logger.error(f"Error syncing {tab_name} strategy stocks: {e}")
    
    logger.info("Sync process completed.")

def fetch_live_ltp():
    """Fetch live LTP from Google Sheet CSV export with caching."""
    cache_key = 'live_ltp_data'
    data = cache.get(cache_key)
    
    if data is not None:
        return data

    url = "https://docs.google.com/spreadsheets/d/12eLJHTlHO1naQgJ-dzf-UTgUbasVv02tgwlHKofG2Y4/export?format=csv"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Read CSV, skipping first row as it might be header
        df = pd.read_csv(io.StringIO(response.text), skiprows=1)
        
        ltp_map = {}
        for _, row in df.iterrows():
            try:
                # Assuming Column 2 is Symbol and Column 4 is LTP based on other sync logic
                symbol = str(row.iloc[2]).strip().upper()
                ltp_val = row.iloc[4]
                
                if pd.notna(symbol) and pd.notna(ltp_val):
                    try:
                        price = float(ltp_val)
                        if not math.isnan(price):
                            ltp_map[symbol] = price
                    except (ValueError, TypeError):
                        continue
            except Exception:
                continue
                
        # Cache for 5 minutes
        cache.set(cache_key, ltp_map, 300)
        return ltp_map
        
    except Exception as e:
        logger.error(f"Error in fetch_live_ltp: {e}")
        return {}

def fetch_strategy_stocks():
    """Fetch recommended stocks for each strategy from the database (synced from Google Sheets)."""
    from core.models import Strategy
    
    # Use cache to avoid frequent DB hits if preferred, though DB is already fast
    cache_key = 'strategy_stocks_db_v1'
    cached = cache.get(cache_key)
    if cached:
        return cached

    result = {}
    strategies = Strategy.objects.all().prefetch_related('stocks')
    for strategy in strategies:
        result[strategy.name] = list(strategy.stocks.values_list('symbol', flat=True))
    
    if result:
        cache.set(cache_key, result, 300) # cache for 5 minutes
    return result

def get_recommendations(user):
    """
    Calculate buy/sell recommendations for a given user.
    Extracted from dashboard view for reusability.
    """
    from core.models import Portfolio, PnLStatement, Instrument, Profile
    
    portfolio_items = Portfolio.objects.filter(user=user).select_related('instrument')
    live_ltps = fetch_live_ltp() or {}
    pnl_items = PnLStatement.objects.filter(user=user).select_related('instrument')
    
    # Aggregate Realized Profit per Instrument
    realized_profits_qs = pnl_items.annotate(
        symbol_upper=Upper('instrument__symbol')
    ).values('symbol_upper').annotate(
        total_profit=Sum('realized_profit')
    )
    realized_profits = {item['symbol_upper'].upper(): float(item['total_profit']) for item in realized_profits_qs}

    # Map symbols to strategies
    strategy_stocks = fetch_strategy_stocks()
    symbol_to_strategy = {}
    for s_key, s_list in strategy_stocks.items():
        for s in s_list:
            symbol_to_strategy[s.upper()] = s_key

    def get_factor_j(lh_diff):
        if lh_diff is None: return 1.0
        lh_diff = float(lh_diff)
        if lh_diff <= 2: return 0.5
        if lh_diff <= 5: return 0.55
        if lh_diff <= 8: return 0.6
        if lh_diff <= 12: return 0.68
        if lh_diff <= 18: return 0.75
        if lh_diff <= 25: return 0.85
        if lh_diff <= 35: return 0.92
        return 0.97

    def get_factor_i(pe):
        if pe is None or pe == 0: return 0.3
        pe = float(pe)
        if pe < 0: return 0.3333333333
        if pe == 50: return 1.0
        if pe > 50: return 50.0 / pe
        return 1.0

    profile, _ = Profile.objects.get_or_create(user=user)
    portfolio_symbols = {item.instrument.symbol.upper() for item in portfolio_items}
    recommendations = []

    for item in portfolio_items:
        symbol = item.instrument.symbol
        quantity = item.quantity
        avg_cost = float(item.avg_cost)
        
        ltp = float(live_ltps.get(symbol.upper(), 0))
        if ltp <= 0:
            try:
                ltp = float(item.instrument.last_price)
            except (AttributeError, ValueError, TypeError):
                ltp = 0
        if ltp <= 0:
            ltp = float(item.ltp)
        
        invested = quantity * avg_cost
        current = quantity * ltp
        unrealized = current - invested
        unrealized_pct = (unrealized / invested * 100) if invested else 0
        
        realized_profit = realized_profits.get(symbol.upper(), 0)
        strat_key = symbol_to_strategy.get(symbol.upper(), 'moderate')
        initial_inv = float(profile.get_max_investment(strat_key))
        
        factor_j = get_factor_j(item.instrument.diff_from_lh_pct)
        factor_i = get_factor_i(item.instrument.pe_ratio)
        
        buy_gap_formula = (realized_profit * 0.93 - invested) + (initial_inv * factor_j * factor_i)
        
        if unrealized_pct >= 22:
            action = "SELL"
            reason = f"Pft {unrealized_pct:.2f}% >= 22%"
        elif -3000 <= buy_gap_formula <= 3000:
            action = "HOLD"
            reason = f"TgtCap: {buy_gap_formula:.0f}"
        elif buy_gap_formula > 3000:
            action = "BUY"
            reason = f"TgtCap: {buy_gap_formula:.0f}"
        elif buy_gap_formula < -3000:
            action = "REDUCE"
            reason = f"TgtCap: {buy_gap_formula:.0f}"
        else:
            action = "HOLD"
            reason = "Stable"

        buy_gap = buy_gap_formula if action == 'BUY' else 0
        reduce_gap = abs(buy_gap_formula) if action == 'REDUCE' else 0

        recommendations.append({
            'symbol': symbol,
            'name': item.instrument.name,
            'quantity': quantity,
            'avg_cost': avg_cost,
            'ltp': ltp,
            'invested_amount': round(invested, 2),
            'current_value': round(current, 2),
            'unrealized_pnl': round(unrealized, 2),
            'pnl_percent': round(unrealized_pct, 2),
            'action': action,
            'reason': reason,
            'portfolio_id': item.id,
            'instrument_id': item.instrument.id,
            'buy_gap': round(buy_gap, 2),
            'reduce_gap': round(reduce_gap, 2),
            'realized_profit': realized_profit,
            'in_portfolio': True if quantity > 0 else False,
        })
    
    # Add P&L-only stocks
    for symbol, realized_profit in realized_profits.items():
        symbol = symbol.upper()
        if symbol not in portfolio_symbols:
            inst = Instrument.objects.filter(symbol__iexact=symbol).first()
            if not inst: continue
            
            ltp = float(live_ltps.get(symbol, 0))
            if ltp <= 0: ltp = float(inst.last_price or 0)

            strat_key = symbol_to_strategy.get(symbol, 'moderate')
            initial_inv = float(profile.get_max_investment(strat_key))
            factor_j = get_factor_j(inst.diff_from_lh_pct)
            factor_i = get_factor_i(inst.pe_ratio)
            
            buy_gap_formula = (realized_profit * 0.93) + (initial_inv * factor_j * factor_i)
            
            if -3000 <= buy_gap_formula <= 3000:
                action = "HOLD"
            elif buy_gap_formula > 3000:
                action = "BUY"
            elif buy_gap_formula < -3000:
                action = "REDUCE"
            else:
                action = "HOLD"

            buy_gap = buy_gap_formula if action == 'BUY' else 0
            reduce_gap = abs(buy_gap_formula) if action == 'REDUCE' else 0

            recommendations.append({
                'symbol': symbol,
                'name': inst.name if inst else symbol,
                'quantity': 0,
                'avg_cost': 0,
                'ltp': ltp,
                'invested_amount': 0,
                'current_value': 0,
                'unrealized_pnl': 0,
                'pnl_percent': 0,
                'action': action,
                'buy_gap': round(buy_gap, 2),
                'reduce_gap': round(reduce_gap, 2),
                'realized_profit': realized_profit,
                'in_portfolio': False,
            })
        
    # Add Strategy symbols not in portfolio or P&L
    all_strategy_symbols = set()
    for s_list in strategy_stocks.values():
        all_strategy_symbols.update(s_list)
    
    processed_symbols = portfolio_symbols.union(set(realized_profits.keys()))
    
    for symbol in all_strategy_symbols:
        symbol = symbol.upper()
        if symbol not in processed_symbols:
            inst = Instrument.objects.filter(symbol__iexact=symbol).first()
            ltp = float(live_ltps.get(symbol, 0))
            if inst and ltp <= 0: ltp = float(inst.last_price or 0)
            
            strat_key = symbol_to_strategy.get(symbol, 'moderate')
            initial_inv = float(profile.get_max_investment(strat_key))
            
            factor_j = 1.0
            factor_i = 1.0
            if inst:
                factor_j = get_factor_j(inst.diff_from_lh_pct)
                factor_i = get_factor_i(inst.pe_ratio)
            
            buy_gap_formula = initial_inv * factor_j * factor_i
            
            if -3000 <= buy_gap_formula <= 3000:
                action = "HOLD"
            elif buy_gap_formula > 3000:
                action = "BUY"
            elif buy_gap_formula < -3000:
                action = "REDUCE"
            else:
                action = "HOLD"

            buy_gap = buy_gap_formula if action == 'BUY' else 0
            reduce_gap = abs(buy_gap_formula) if action == 'REDUCE' else 0

            recommendations.append({
                'symbol': symbol,
                'name': inst.name if inst else symbol,
                'quantity': 0,
                'avg_cost': 0,
                'ltp': ltp,
                'invested_amount': 0,
                'current_value': 0,
                'unrealized_pnl': 0,
                'pnl_percent': 0,
                'action': action,
                'buy_gap': round(buy_gap, 2),
                'reduce_gap': round(reduce_gap, 2),
                'realized_profit': 0,
                'in_portfolio': False,
            })
            
    return recommendations, realized_profits, strategy_stocks
