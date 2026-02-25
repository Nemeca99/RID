# conftest.py — ensures 'rid' package is importable from any test
import sys
from pathlib import Path

# Add repo root to path so `import rid` works
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
