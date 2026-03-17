from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import EmailOrMobileAuthenticationForm

urlpatterns = [
    path('search-instruments/', views.search_instruments, name='search_instruments'),
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('register/send-otp/', views.send_signup_otp, name='send_signup_otp'),
    path('register/verify-otp/', views.verify_signup_otp, name='verify_signup_otp'),
    path('upload/portfolio/', views.upload_portfolio, name='upload_portfolio'),
    path('portfolio/add/', views.add_portfolio_item, name='add_portfolio_item'),

    path('upload/pnl/', views.upload_pnl, name='upload_pnl'),
    path('portfolio/edit/<int:pk>/', views.edit_portfolio_item, name='edit_portfolio_item'),
    path('portfolio/delete/<int:pk>/', views.delete_portfolio_item, name='delete_portfolio_item'),
    path('portfolio/buy/', views.buy_stock, name='buy_stock'),
    path('portfolio/sell/', views.sell_stock, name='sell_stock'),
    
    # Custom Login View
    path('accounts/login/', auth_views.LoginView.as_view(authentication_form=EmailOrMobileAuthenticationForm), name='login'),
    path('strategy/', views.strategy, name='strategy'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('mf-guide/', views.mf_guide, name='mf_guide'),
    path('stock-guide/', views.stock_guide, name='stock_guide'),
    path('etf-guide/', views.etf_guide, name='etf_guide'),
    path('nps-guide/', views.nps_guide, name='nps_guide'),
    path('donation/', views.donation, name='donation'),
    path('aboutproject/', views.about_project, name='about_project'),
    # Transactions and Lots
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('portfolio/lots/<int:instrument_id>/', views.lot_breakdown, name='lot_breakdown'),
    path('portfolio/lot/edit/<int:pk>/', views.edit_lot, name='edit_lot'),
    path('portfolio/lot/delete/<int:pk>/', views.delete_lot, name='delete_lot'),

    # Forgot Password Flow
    path('accounts/password_change/forgot/', views.forgot_password_session, name='forgot_password_session'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    
    # Internal Sync API
    path('api/sync-data/', views.sync_data_api, name='sync_data_api'),
    path('api/index-data/', views.index_data_api, name='index_data_api'),
    path('api/stock-price/', views.stock_price_api, name='stock_price_api'),
    path('api/stock-suggestions/', views.stock_suggestions_api, name='stock_suggestions_api'),
    path('api/stock-history/', views.stock_history_api, name='stock_history_api'),
    path('.well-known/assetlinks.json', views.assetlinks_json, name='assetlinks_json'),
]
