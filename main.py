import asyncio
import base64
import os
import tempfile
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agent import main
from app.config.logging import setup_logger

load_dotenv()

WAIT_TIME = os.getenv("WAIT_TIME", 1)
LANG = os.getenv("LANGUAGE")

logger = setup_logger()

message_buffers = defaultdict(list)
processing_tasks = {}


class Sender(BaseModel):
    """Simplified sender information"""

    id: str
    isUser: bool


class WebhookMessage(BaseModel):
    """Only the essential fields from the webhook message"""

    event: str
    session: str
    body: str
    type: str
    isNewMsg: bool
    sender: Sender
    isGroupMsg: bool


async def transcribe_base64_audio(base64_audio: str) -> str:
    """Transcribe audio from base64 data using OpenAI Whisper"""
    try:
        # Decode base64 audio data
        audio_data = base64.b64decode(base64_audio)

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
            tmp_file.write(audio_data)
            tmp_file_path = tmp_file.name

        # Transcribe the audio
        with open(tmp_file_path, "rb") as audio_file:
            transcription = GROQ_CLIENT.audio.transcriptions.create(
                model="whisper-large-v3", file=audio_file, language=LANG
            )
        return transcription.text
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


async def process_aggregated_messages(
    sender_id: str, session: str, is_user: bool, is_group: bool
):
    """Process messages after waiting period"""
    try:
        # Wait for X seconds to aggregate messages
        await asyncio.sleep(int(WAIT_TIME))

        # Get all messages for this sender
        messages = message_buffers[sender_id]
        if not messages:
            return

        # Combine all messages
        combined_message = " ".join([msg for msg in messages])

        # Clear the buffer
        message_buffers[sender_id] = []

        # Remove the task from processing_tasks
        if sender_id in processing_tasks:
            del processing_tasks[sender_id]

        # Process the combined message
        phone_number = sender_id.split("@")[0]

        logger.info(
            f"Processing aggregated messages for {sender_id}: {combined_message}"
        )
        agent_response = await main(phone_number, combined_message)

        logger.info(f"Agent response for aggregated messages: {agent_response}")

        return {
            "status": "success",
            "processed_data": {
                "session": session,
                "message": combined_message,
                "sender_id": sender_id,
                "is_user": is_user,
                "is_group": is_group,
            },
            "agent_response": agent_response,
        }

    except Exception as e:
        logger.error(f"Error processing aggregated messages: {str(e)}")
        # Clear the buffer in case of error
        message_buffers[sender_id] = []
        if sender_id in processing_tasks:
            del processing_tasks[sender_id]
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info("WebHook service starting up")
    yield
    logger.info("WebHook service shutting down")


app = FastAPI(title="WPPConnect Message Parser", lifespan=lifespan)


@app.post("/webhook")
async def webhook_handler(data: Dict[str, Any]):
    """
    Handles incoming webhooks from WPPConnect, processing both text and audio messages
    """
    request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    logger.info(f"Received webhook request - ID: {request_id}")

    try:
        # Check if this is a message we want to process
        if (
            data.get("event") == "onmessage"
            and data.get("isNewMsg") == True
            and data.get("type")
            in ["chat", "list_response", "ptt"]  # Added 'ptt' for voice messages
        ):
            try:
                message_text = data.get("body", "")

                # Handle audio messages
                if data.get("type") == "ptt":
                    logger.info(f"Request {request_id} - Processing audio message")
                    try:
                        # Transcribe base64 audio data
                        message_text = await transcribe_base64_audio(message_text)
                        logger.info(
                            f"Request {request_id} - Audio transcribed: {message_text}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Request {request_id} - Error processing audio: {str(e)}"
                        )
                        raise HTTPException(
                            status_code=422, detail=f"Error processing audio: {str(e)}"
                        )

                # Parse the message
                message = WebhookMessage(
                    event=data["event"],
                    session=data["session"],
                    body=message_text,  # Use transcribed text for audio messages
                    type=data["type"],
                    isNewMsg=data["isNewMsg"],
                    sender=Sender(
                        id=data["sender"]["id"], isUser=data["sender"]["isUser"]
                    ),
                    isGroupMsg=data["isGroupMsg"],
                )

                sender_id = message.sender.id

                # Add message to buffer
                message_buffers[sender_id].append(message.body)

                # If this is the first message from this sender, create a new processing task
                if sender_id not in processing_tasks:
                    task = asyncio.create_task(
                        process_aggregated_messages(
                            sender_id,
                            message.session,
                            message.sender.isUser,
                            message.isGroupMsg,
                        )
                    )
                    processing_tasks[sender_id] = task

                    return {
                        "status": "aggregating",
                        "message": "Message received and being aggregated",
                    }
                else:
                    # If we already have a task running, just acknowledge the message
                    return {
                        "status": "aggregating",
                        "message": "Message added to existing aggregation window",
                    }

            except Exception as e:
                logger.error(f"Request {request_id} - Error parsing message: {str(e)}")
                raise HTTPException(
                    status_code=422, detail=f"Error parsing message: {str(e)}"
                )

        # Log skipped messages
        logger.info(f"Request {request_id} - Message skipped (does not match criteria)")
        return {
            "status": "received",
            "message": "Message received but not processed (not matching criteria)",
        }

    except Exception as e:
        logger.error(f"Request {request_id} - Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error processing webhook: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    logger.info("Health check requested")
    return {"status": "healthy"}