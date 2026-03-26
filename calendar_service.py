"""
Google Calendar API integration using service account.
"""

import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import settings

logger = logging.getLogger("AsherBot")

TIMEZONE = ZoneInfo(settings.TIMEZONE)
TZ_NAME = settings.TIMEZONE


def _get_service():
    """Build the Google Calendar API service."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_file = settings.GOOGLE_CREDENTIALS_FILE
    if not os.path.exists(creds_file):
        raise FileNotFoundError(
            f"קובץ credentials.json לא נמצא ב-{creds_file}. "
            "צריך ליצור service account ב-Google Cloud Console."
        )

    creds = service_account.Credentials.from_service_account_file(
        creds_file,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    return build("calendar", "v3", credentials=creds)


def list_events(date_str: str, days: int = 1) -> str:
    """List calendar events for a date range. Returns formatted string."""
    try:
        service = _get_service()

        start_date = datetime.strptime(date_str, "%Y-%m-%d")
        start_dt = start_date.replace(tzinfo=TIMEZONE)
        end_dt = start_dt + timedelta(days=days)

        events_result = service.events().list(
            calendarId=settings.GOOGLE_CALENDAR_ID,
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])

        if not events:
            if days == 1:
                return f"אין אירועים ביומן ל-{date_str}"
            return f"אין אירועים ביומן בין {date_str} ל-{days} ימים קדימה"

        lines = []
        current_date = ""
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))

            # Parse and format
            if "T" in start:
                event_dt = datetime.fromisoformat(start)
                event_date = event_dt.strftime("%d/%m/%Y")
                event_time = event_dt.strftime("%H:%M")
            else:
                event_date = datetime.strptime(start, "%Y-%m-%d").strftime("%d/%m/%Y")
                event_time = "כל היום"

            if event_date != current_date:
                current_date = event_date
                lines.append(f"\n📅 {current_date}:")

            summary = event.get("summary", "(ללא כותרת)")
            lines.append(f"  {event_time} - {summary}")

        return "\n".join(lines).strip()

    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        logger.error(f"Calendar list error: {e}")
        return f"שגיאה בגישה ליומן: {str(e)}"


def create_event(
    summary: str,
    date: str,
    start_time: str,
    end_time: str = None,
    description: str = None,
) -> str:
    """Create a calendar event. Returns confirmation string."""
    try:
        service = _get_service()

        # Parse start time
        start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        start_dt = start_dt.replace(tzinfo=TIMEZONE)

        # Parse or default end time
        if end_time:
            end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
            end_dt = end_dt.replace(tzinfo=TIMEZONE)
        else:
            end_dt = start_dt + timedelta(hours=1)

        event_body = {
            "summary": summary,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": TZ_NAME},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": TZ_NAME},
        }

        if description:
            event_body["description"] = description

        event = service.events().insert(
            calendarId=settings.GOOGLE_CALENDAR_ID,
            body=event_body,
        ).execute()

        display_date = start_dt.strftime("%d/%m/%Y")
        display_time = start_dt.strftime("%H:%M")
        return f"✅ אירוע נוצר: {summary} ב-{display_date} בשעה {display_time}"

    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        logger.error(f"Calendar create error: {e}")
        return f"שגיאה ביצירת אירוע: {str(e)}"
