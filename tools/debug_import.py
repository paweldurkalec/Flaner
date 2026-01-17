import sys
import os
print('DEBUG: starting import test')
src_path = os.path.join(os.getcwd(), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
try:
    import flaner
    print('DEBUG: flaner imported successfully')
except Exception:
    import traceback
    traceback.print_exc()
