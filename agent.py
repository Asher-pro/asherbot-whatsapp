"""
AsherBot - AI conversation logic with Claude tool_use.
"""

import logging

from anthropic import Anthropic

from config import settings
from database import get_history, save_message
from tools import TOOLS, execute_tool

logger = logging.getLogger("AsherBot")

client = Anthropic()


def get_response(phone: str, message: str, sender_name: str = "") -> str:
    """Process a message and return an AI response using Claude tool_use."""

    # Load conversation history
    history = get_history(phone, limit=settings.MAX_HISTORY)

    # Build messages for Claude
    messages = list(history)
    messages.append({"role": "user", "content": message})

    # Tool use loop (max 5 iterations)
    for _ in range(5):
        response = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=1024,
            system=settings.SYSTEM_PROMPT,
            messages=messages,
            tools=TOOLS,
        )

        # If Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Add assistant response to messages
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"Tool call: {block.name}({block.input})")
                    result = execute_tool(block.name, block.input, phone)
                    logger.info(f"Tool result: {result[:100]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Feed results back to Claude
            messages.append({"role": "user", "content": tool_results})
            continue

        # Claude produced a final text response
        break

    # Extract text reply
    reply = ""
    for block in response.content:
        if hasattr(block, "text"):
            reply += block.text

    if not reply:
        reply = "סליחה, לא הצלחתי לעבד את הבקשה."

    # Save only original message + final reply to history
    save_message(phone, "user", message)
    save_message(phone, "assistant", reply)

    return reply
