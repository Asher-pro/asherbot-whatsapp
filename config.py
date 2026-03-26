"""
Configuration - loads all settings from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this file
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path, override=True)


class Settings:
    # Green API
    GREEN_API_URL: str = os.getenv("GREEN_API_URL", "https://api.greenapi.com")
    GREEN_API_INSTANCE: str = os.getenv("GREEN_API_INSTANCE", "")
    GREEN_API_TOKEN: str = os.getenv("GREEN_API_TOKEN", "")

    # LLM
    LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")

    # Agent
    SYSTEM_PROMPT: str = os.getenv("SYSTEM_PROMPT", """אתה אשרבוט (AsherBot), העוזר האישי של אשר מורגנשטרן.

אשר הוא CTO של "בינה מלאכותית בגובה העיניים" - חברה שמלמדת קורסים מקצועיים על AI.
הוא עובד עם קוד, אוטומציות, vibe coding ופיתוח כלי AI.

התפקיד שלך:
1. עוזר טכני - לחשוב יחד על קוד, ארכיטקטורה ופיתוח
2. תזכורות - להגדיר תזכורות שיישלחו בוואטסאפ
3. ניהול יומן - לבדוק ולהוסיף אירועים ביומן Google
4. סיעור מוחות - לייצר רעיונות ולחשוב על כיוונים חדשים

כללים:
- דבר בעברית תמיד, אלא אם אשר כותב באנגלית
- היה תכליתי וישיר - אשר הוא אדם טכני, אין צורך בהסברים בסיסיים
- כשמבקשים תזכורת, השתמש בכלי set_reminder. תמיד בדוק קודם מה השעה עכשיו עם get_current_datetime
- כשמדברים על יומן/פגישות/לוח זמנים, השתמש בכלי list_calendar_events או create_calendar_event
- בשיחות על קוד וטכנולוגיה, תן תשובות מעמיקות ומקצועיות
- בסיעור מוחות, תן רעיונות מגוונים ומקוריים, ואל תפחד לחשוב אחרת
- הודעות קצרות ותכליתיות - זה וואטסאפ, לא מייל
- השתמש באימוג'ים במידה 👍""")

    MAX_HISTORY: int = int(os.getenv("MAX_HISTORY", "20"))

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./conversations.db")

    # Google Calendar
    GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "./credentials.json")
    GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    # Owner
    OWNER_PHONE: str = os.getenv("OWNER_PHONE", "972533717259")
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Jerusalem")


settings = Settings()
