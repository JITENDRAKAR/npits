from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import os
        from django.core.management import call_command
        
        def run_alerts():
            try:
                call_command('send_signal_alerts')
            except Exception as e:
                print(f"Error running signal alerts: {e}")

        # Ensure scheduler only runs once in the main process
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('SERVER_SOFTWARE', '').startswith('gunicorn'):
            from .utils import perform_sync
            from apscheduler.schedulers.background import BackgroundScheduler
            
            scheduler = BackgroundScheduler()
            scheduler.add_job(perform_sync, 'interval', minutes=1, id='gsheet_sync_job', replace_existing=True)
            # Run alerts check every 4 hours
            scheduler.add_job(run_alerts, 'interval', hours=4, id='signal_alert_job', replace_existing=True)
            scheduler.start()
            print("Background scheduler started for Google Sheets sync & alerts.")
        elif not os.environ.get('RUN_MAIN'):
            # Fallback for other environments like IIS
            from .utils import perform_sync
            from apscheduler.schedulers.background import BackgroundScheduler
            
            scheduler = BackgroundScheduler()
            scheduler.add_job(perform_sync, 'interval', minutes=1, id='gsheet_sync_job', replace_existing=True)
            # Run alerts check every 4 hours
            scheduler.add_job(run_alerts, 'interval', hours=4, id='signal_alert_job', replace_existing=True)
            scheduler.start()
            print("Background scheduler started (IIS/Generic) with alerts.")
