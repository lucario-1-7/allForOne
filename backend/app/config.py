import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./allforone.db")

TMDB_TOKEN = os.getenv("TMDB_TOKEN", "")
FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN", "")
BALLDONTLIE_KEY = os.getenv("BALLDONTLIE_KEY", "")
IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID", "")
IGDB_CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET", "")
VLRGG_BASE_URL = os.getenv("VLRGG_BASE_URL", "")

# Optional shared cache. Leave empty to use the in-process dict (fine for one
# instance / free tier). Set to a Redis URL to scale across instances.
REDIS_URL = os.getenv("REDIS_URL", "")
CRICAPI_KEY = os.getenv("CRICAPI_KEY", "")          # cricketdata.org (cricket)
API_SPORTS_KEY = os.getenv("API_SPORTS_KEY", "")    # api-sports.io (tennis, beta)

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days
HTTP_TIMEOUT = 12.0
