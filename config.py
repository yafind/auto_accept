import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_id: int
    database_path: str
    heartbeat_interval: int
    digest_time: str
    channels_file: Path = BASE_DIR / "channels.txt"
    messages_file: Path = BASE_DIR / "messages.json"


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token == "your_bot_token":
        raise ValueError("BOT_TOKEN is not configured in .env")
    return Settings(
        bot_token=token,
        admin_id=int(os.getenv("ADMIN_ID", "0")),
        database_path=os.getenv("DATABASE_PATH", str(BASE_DIR / "bot.db")),
        heartbeat_interval=int(os.getenv("HEARTBEAT_INTERVAL", "3600")),
        digest_time=os.getenv("DIGEST_TIME", "09:00"),
    )
