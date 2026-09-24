"""Desktop entry point: double-click to launch; automation passes --no-open."""
import multiprocessing
import sys
from instinct_bridge.web import main

if __name__ == '__main__':
    multiprocessing.freeze_support()
    if '--no-open' in sys.argv:
        sys.argv.remove('--no-open')
    else:
        sys.argv.append('--open')
    main()
