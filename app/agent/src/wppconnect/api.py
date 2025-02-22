import base64
import logging
import os
from typing import Dict

import requests

logger = logging.getLogger(__name__)


class WhatsAppConnection:
    def __init__(self):
        self.base_url = os.getenv("WPPCONNECT_BASE_URL", "").rstrip("/")
        self.session = os.getenv("WPPCONNECT_SESSION_NAME")
        self.secret_key = os.getenv("WPPCONNECT_SECRET_KEY")
        self.token = os.getenv("WPPCONNECT_TOKEN")
        self.full_token = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _generate_token(self):
        url = f"{self.base_url}/api/{self.session}/{self.secret_key}/generate-token"
        try:
            response = requests.post(url)
            response.raise_for_status()
            data = response.json()
            self.full_token = data.get("full")
            self.token = data.get("token")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error generating token: {e}")
            raise


def send_message(message: str, phone_number: str) -> Dict:
    """Send a WhatsApp message to a specified phone number."""

    if not phone_number:
        raise ValueError("Missing phone_number")

    with WhatsAppConnection() as conn:
        url = f"{conn.base_url}/api/{conn.session}/send-message"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Authorization": f"Bearer {conn.token}",
        }

        data = {"phone": phone_number, "message": message}

        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message: {e}")
            raise


def send_voice(audio_path: str, phone_number: str) -> Dict:
    """Send a WhatsApp voice message to a specified phone number."""

    if not phone_number:
        raise ValueError("Missing phone_number")

    if not audio_path:
        raise ValueError("Missing audio file path")

    # Convert audio file to base64
    try:
        with open(audio_path, "rb") as audio_file:
            base64_audio = base64.b64encode(audio_file.read()).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Error reading audio file: {e}")

    with WhatsAppConnection() as conn:
        url = f"{conn.base_url}/api/{conn.session}/send-voice-base-64"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Authorization": f"Bearer {conn.token}",
        }

        data = {
            "phone": phone_number,
            "isGroup": False,
            "base64": f"data:audio/mpeg;base64,{base64_audio}",
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending voice message: {e}")
            raise
