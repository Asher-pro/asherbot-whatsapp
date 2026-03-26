"""
AsherBot - WhatsApp AI Agent
Webhook server that receives messages from Green API and responds using Claude.
Includes background task for delivering reminders.
"""

import asyncio
import hashlib
import time
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config import settings
from agent import get_response
from database import init_db, get_due_reminders, mark_reminder_delivered

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AsherBot")

# Simple deduplication: track recent message IDs
_seen_messages: dict[str, float] = {}
DEDUP_WINDOW = 60  # seconds


def _cleanup_seen():
    now = time.time()
    expired = [k for k, v in _seen_messages.items() if now - v > DEDUP_WINDOW]
    for k in expired:
        del _seen_messages[k]


async def reminder_loop():
    """Check for due reminders every 60 seconds and send them via WhatsApp."""
    while True:
        try:
            due = get_due_reminders()
            for reminder in due:
                chat_id = f"{reminder['phone']}@c.us"
                text = f"⏰ תזכורת: {reminder['reminder_text']}"
                try:
                    await send_whatsapp_message(chat_id, text)
                    mark_reminder_delivered(reminder["id"])
                    logger.info(f"Reminder #{reminder['id']} delivered to {reminder['phone']}")
                except Exception as e:
                    logger.error(f"Failed to deliver reminder #{reminder['id']}: {e}")
        except Exception as e:
            logger.error(f"Reminder loop error: {e}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(reminder_loop())
    logger.info("AsherBot is ready 🤖")
    yield
    task.cancel()


app = FastAPI(title="AsherBot", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "AsherBot"}


@app.post("/webhook/green-api")
async def webhook(request: Request):
    """Handle incoming messages from Green API."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    # Only process incoming text messages
    webhook_type = data.get("typeWebhook")
    if webhook_type != "incomingMessageReceived":
        return {"ok": True, "skipped": webhook_type}

    message_data = data.get("messageData", {})
    message_type = message_data.get("typeMessage")
    if message_type != "textMessage":
        return {"ok": True, "skipped": message_type}

    # Extract sender and message
    sender_data = data.get("senderData", {})
    chat_id = sender_data.get("chatId", "")
    sender_name = sender_data.get("senderName", "")
    text = message_data.get("textMessageData", {}).get("textMessage", "")
    message_id = data.get("idMessage", "")

    # Skip group messages
    if "@g.us" in chat_id:
        return {"ok": True, "skipped": "group_message"}

    # Skip empty messages
    if not text.strip():
        return {"ok": True, "skipped": "empty"}

    # Deduplication
    _cleanup_seen()
    if message_id in _seen_messages:
        return {"ok": True, "skipped": "duplicate"}
    _seen_messages[message_id] = time.time()

    # Extract phone number
    phone = chat_id.replace("@c.us", "")

    logger.info(f"Message from {sender_name} ({phone}): {text[:50]}...")

    # Get AI response
    try:
        reply = get_response(phone, text, sender_name)
    except Exception as e:
        logger.error(f"Agent error: {e}")
        reply = "סליחה, משהו השתבש. נסה שוב בעוד רגע 🙏"

    # Send reply via Green API
    try:
        await send_whatsapp_message(chat_id, reply)
        logger.info(f"Reply sent to {phone}: {reply[:50]}...")
    except Exception as e:
        logger.error(f"Failed to send reply: {e}")

    return {"ok": True}


async def send_whatsapp_message(chat_id: str, message: str):
    """Send a text message via Green API."""
    url = (
        f"{settings.GREEN_API_URL}"
        f"/waInstance{settings.GREEN_API_INSTANCE}"
        f"/sendMessage/{settings.GREEN_API_TOKEN}"
    )
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json={"chatId": chat_id, "message": message},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
