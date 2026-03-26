"""
Tool definitions for Claude tool_use + dispatch function.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import settings
from database import create_reminder, get_pending_reminders
from calendar_service import list_events, create_event

TIMEZONE = ZoneInfo(settings.TIMEZONE)

# --- Tool Definitions (JSON schemas for Claude API) ---

TOOLS = [
    {
        "name": "get_current_datetime",
        "description": "קבל את התאריך והשעה הנוכחיים באזור הזמן של ישראל. השתמש בכלי הזה כשצריך לדעת מה השעה או התאריך, או לפני הגדרת תזכורת.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_calendar_events",
        "description": "הצג אירועים מיומן Google. השתמש כשהמשתמש שואל מה יש ביומן, מה הפגישות, או מה מתוכנן.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "תאריך בפורמט YYYY-MM-DD. ברירת מחדל: היום.",
                },
                "days": {
                    "type": "integer",
                    "description": "כמה ימים קדימה להציג. ברירת מחדל: 1. מקסימום: 7.",
                    "default": 1,
                },
            },
            "required": [],
        },
    },
    {
        "name": "create_calendar_event",
        "description": "צור אירוע חדש ביומן Google. השתמש כשהמשתמש רוצה להוסיף פגישה או אירוע ליומן.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "שם/כותרת האירוע",
                },
                "date": {
                    "type": "string",
                    "description": "תאריך האירוע בפורמט YYYY-MM-DD",
                },
                "start_time": {
                    "type": "string",
                    "description": "שעת התחלה בפורמט HH:MM (24 שעות). למשל: 14:30",
                },
                "end_time": {
                    "type": "string",
                    "description": "שעת סיום בפורמט HH:MM. אם לא צוין, שעה אחרי ההתחלה.",
                },
                "description": {
                    "type": "string",
                    "description": "תיאור או הערות לאירוע (אופציונלי)",
                },
            },
            "required": ["summary", "date", "start_time"],
        },
    },
    {
        "name": "set_reminder",
        "description": "הגדר תזכורת שתישלח כהודעת WhatsApp בזמן שנקבע. השתמש כשהמשתמש מבקש שתזכיר לו משהו.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "טקסט התזכורת",
                },
                "date": {
                    "type": "string",
                    "description": "תאריך התזכורת בפורמט YYYY-MM-DD",
                },
                "time": {
                    "type": "string",
                    "description": "שעת התזכורת בפורמט HH:MM (24 שעות)",
                },
            },
            "required": ["text", "date", "time"],
        },
    },
    {
        "name": "list_reminders",
        "description": "הצג את כל התזכורות הממתינות. השתמש כשהמשתמש שואל אילו תזכורות יש לו.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# --- Tool Execution ---

def execute_tool(tool_name: str, tool_input: dict, phone: str) -> str:
    """Execute a tool and return the result as a string."""
    try:
        if tool_name == "get_current_datetime":
            now = datetime.now(TIMEZONE)
            return now.strftime("%Y-%m-%d %H:%M:%S (%A)")

        elif tool_name == "list_calendar_events":
            date_str = tool_input.get("date")
            days = tool_input.get("days", 1)
            if not date_str:
                date_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
            days = min(days, 7)
            return list_events(date_str, days)

        elif tool_name == "create_calendar_event":
            return create_event(
                summary=tool_input["summary"],
                date=tool_input["date"],
                start_time=tool_input["start_time"],
                end_time=tool_input.get("end_time"),
                description=tool_input.get("description"),
            )

        elif tool_name == "set_reminder":
            text = tool_input["text"]
            date_str = tool_input["date"]
            time_str = tool_input["time"]

            # Parse local time and convert to UTC for storage
            local_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            local_dt = local_dt.replace(tzinfo=TIMEZONE)
            utc_dt = local_dt.astimezone(ZoneInfo("UTC"))

            reminder_id = create_reminder(
                phone=phone,
                text=text,
                remind_at=utc_dt.strftime("%Y-%m-%d %H:%M:%S"),
            )
            local_display = local_dt.strftime("%d/%m/%Y %H:%M")
            return f"תזכורת #{reminder_id} נקבעה ל-{local_display}: {text}"

        elif tool_name == "list_reminders":
            reminders = get_pending_reminders(phone)
            if not reminders:
                return "אין תזכורות ממתינות."
            lines = []
            for r in reminders:
                # Convert stored UTC to local time for display
                utc_dt = datetime.strptime(r["remind_at"], "%Y-%m-%d %H:%M:%S")
                utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
                local_dt = utc_dt.astimezone(TIMEZONE)
                lines.append(f"#{r['id']} - {local_dt.strftime('%d/%m/%Y %H:%M')} - {r['reminder_text']}")
            return "\n".join(lines)

        else:
            return f"כלי לא מוכר: {tool_name}"

    except Exception as e:
        return f"שגיאה בהפעלת הכלי: {str(e)}"
