import os
import sys
import tempfile
from pathlib import Path

# Import-time DB/key creation must never touch a real PenguCost data directory.
_data = tempfile.TemporaryDirectory(prefix='pengucost-tests-')
os.environ['PENGUCOST_DATA_DIR'] = _data.name
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
