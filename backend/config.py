import os
from dotenv import load_dotenv

# Load from project root .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
KILO_API_KEY = os.getenv("KILO_API_KEY", "")
KILO_MODEL = os.getenv("KILO_MODEL", "kilo-auto/free")
GEMINI_MODEL = "gemini-2.0-flash"

# Provider priority: Kilo → Gemini
LLM_PROVIDER = "kilo" if KILO_API_KEY else "gemini"
