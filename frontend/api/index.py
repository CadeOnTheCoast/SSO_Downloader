import os
import sys

# Add backend and scripts to path so imports work
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../scripts'))

from api import app

# Vercel needs a handler, but FastAPI 'app' is enough if configured correctly in vercel.json
# Usually vercel/python looks for 'app' variable.
