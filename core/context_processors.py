from .utils import get_recommendations

def signal_info(request):
    """
    Context processor to provide buy/sell signal counts to all templates.
    """
    if not request.user.is_authenticated:
        return {}

    try:
        recommendations, _, _ = get_recommendations(request.user)
        
        # Include items currently in portfolio OR P&L Buybacks (Buy signal + realized profit > 0)
        user_signals = [
            r for r in recommendations 
            if r.get('in_portfolio', False) or (r.get('action') == 'BUY' and r.get('realized_profit', 0) > 0)
        ]
        
        buy_count = sum(1 for r in user_signals if r.get('action') == 'BUY')
        reduce_count = sum(1 for r in user_signals if r.get('action') == 'REDUCE')
        sell_count = sum(1 for r in user_signals if r.get('action') == 'SELL')
        
        return {
            'total_signal_count': buy_count + reduce_count + sell_count,
        }
    except Exception as e:
        # Avoid crashing the entire site if recommendation logic fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in signal_info context processor: {e}")
        return {
            'buy_reduce_count': 0,
            'sell_count': 0,
            'has_sell_signal': False,
        }
