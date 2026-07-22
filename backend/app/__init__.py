from __future__ import annotations
import os
from dotenv import load_dotenv

# Load environmental variables at startup
load_dotenv()

# Auto-register all tools when app is imported
import app.tools._register_all
