
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"))

@dataclass
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    channel_username: str = os.getenv("CHANNEL_USERNAME", "")
    show_browser: bool = os.getenv("SHOW_BROWSER", "0") == "1"
    slow_mo_ms: int = int(os.getenv("SLOW_MO", "250"))
    debug_dir: str = os.getenv("DEBUG_DIR", "debug")
    playwright_timeout_ms: int = int(os.getenv("PW_TIMEOUT_MS", "35000"))
    wait_jsonld_ms: int = int(os.getenv("WAIT_JSONLD_MS", "14000"))
    http_timeout: float = float(os.getenv("HTTP_TIMEOUT", "12.0"))
    total_images_limit: int = int(os.getenv("TOTAL_IMAGES_LIMIT", "50"))

settings = Settings()
