import runpy
import traceback
import sys
import os

if __name__ == '__main__':
    # ensure `src` is on sys.path so `from objects.*` imports work
    src_path = os.path.join(os.getcwd(), 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    try:
        runpy.run_path('src/flaner.py', run_name='__main__')
    except Exception:
        traceback.print_exc()
        sys.exit(1)
