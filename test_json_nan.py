import json
import math

data = {
    'prices': [1.0, 2.0, float('nan')]
}

try:
    print(json.dumps(data))
except ValueError as e:
    print(f"Caught expected error: {e}")
