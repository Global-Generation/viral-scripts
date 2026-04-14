import os
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "./downloads")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_API_SECRET = os.getenv("HF_API_SECRET", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
