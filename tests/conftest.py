"""Let tests import the local ogb package without installing it.

CI installs the package with `pip install -e '.[test]'`; verification
environments that cannot modify a PEP 668 system Python rely on this file
instead, so the tests exercise exactly the sources under test.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
