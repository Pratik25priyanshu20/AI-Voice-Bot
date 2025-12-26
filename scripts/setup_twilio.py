"""Helper script to register the webhook on your Twilio number.

Usage:
    python scripts/setup_twilio.py --webhook https://<your-host>/voice
"""

import argparse
import sys
from typing import Optional

from twilio.rest import Client

from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def configure_number(webhook: str, number_sid: str) -> None:
    """Update the Voice webhook on an existing Twilio incoming phone number."""
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    client.incoming_phone_numbers(number_sid).update(
        voice_url=webhook,
        voice_method="POST",
    )
    logger.info("Updated webhook for number %s -> %s", number_sid, webhook)


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure Twilio webhook.")
    parser.add_argument("--webhook", required=False, help="Public https URL to POST /voice")
    parser.add_argument("--number-sid", required=False, help="Twilio IncomingPhoneNumber SID")
    args = parser.parse_args()

    webhook = args.webhook or (settings.public_base_url and f"{settings.public_base_url}/voice")
    if not webhook:
        logger.error("Provide --webhook or set PUBLIC_BASE_URL.")
        sys.exit(1)
    if not args.number_sid:
        logger.error("Provide --number-sid for the Twilio phone number to update.")
        sys.exit(1)

    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.error("Twilio credentials are missing. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.")
        sys.exit(1)

    configure_number(webhook, args.number_sid)


if __name__ == "__main__":
    main()
