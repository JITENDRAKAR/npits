from dateutil import parser
from datetime import datetime, timedelta
import pytz

def test_date_filtering():
    # Mock data
    now = datetime.now(pytz.UTC)
    cutoff = now - timedelta(days=7)
    
    test_dates = [
        (now.strftime("%a, %d %b %Y %H:%M:%S GMT"), True), # Just now
        ((now - timedelta(days=6)).strftime("%a, %d %b %Y %H:%M:%S GMT"), True), # 6 days ago
        ((now - timedelta(days=8)).strftime("%a, %d %b %Y %H:%M:%S GMT"), False), # 8 days ago
        ("Invalid Date", False), # Parsing error
    ]
    
    for date_str, expected in test_dates:
        try:
            dt = parser.parse(date_str)
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            
            result = dt >= cutoff
            print(f"Date: {date_str} | Parsed: {dt} | Expected: {expected} | Result: {result}")
            assert result == expected
        except Exception as e:
            print(f"Date: {date_str} | Error: {e} | Expected: {expected}")
            assert expected == False

if __name__ == "__main__":
    test_date_filtering()
