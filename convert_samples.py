import pandas as pd
import os

files = ['sample_portfolio.csv', 'sample_pnl.csv']
output_dir = 'static/samples'

for f in files:
    if os.path.exists(f):
        df = pd.read_csv(f)
        excel_file = os.path.join(output_dir, f.replace('.csv', '.xlsx'))
        df.to_excel(excel_file, index=False)
        print(f"Converted {f} to {excel_file}")
    else:
        print(f"File {f} not found.")
