import sys
import os

# 1. Point Python to the 'backend' folder so it can find 'data'
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.append(backend_path)

# 2. Now the import works perfectly
from data.fallback import get_option_chain

data, mode = get_option_chain('NIFTY')
print(f"Mode: {mode}")
print(f"Spot: {data['spot']}")
print(f"Strikes: {len(data['strikes'])}")