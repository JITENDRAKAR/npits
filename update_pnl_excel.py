import pandas as pd
import os

data = [
    ["RELIANCE", 5, 11000, 15000, 4000, "2024-12-15", "2025-01-10"],
    ["TCS", 2, 6000, 7500, 1500, "2024-12-20", "2025-01-15"],
    ["INFY", 10, 12000, 13500, 1500, "2025-01-05", "2025-02-01"],
    ["HDFCBANK", 5, 7000, 8000, 1000, "2025-01-15", "2025-02-05"],
    ["ITC", 20, 4000, 5500, 1500, "2025-01-20", "2025-02-10"],
    ["TATAMOTORS", 10, 3500, 4200, 700, "2025-01-25", "2025-02-12"]
]

columns = ["Symbol", "Quantity", "Buy Value", "Sell Value", "Profit", "Entry Date", "Exit Date"]
df = pd.DataFrame(data, columns=columns)

paths = [
    r"c:\inetpub\wwwroot\NPITS\sample_pnl.xlsx",
    r"c:\inetpub\wwwroot\NPITS\static\samples\sample_pnl.xlsx"
]

for p in paths:
    df.to_excel(p, index=False)
    print(f"Updated {p}")
