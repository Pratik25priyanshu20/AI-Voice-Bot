"""Script to place a test outbound call via Twilio to your webhook."""

import argparse
import sys

from twilio.rest import Client

from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def place_call(to_number: str, from_number: str, webhook: str) -> None:
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    call = client.calls.create(
        to=to_number,
        from_=from_number,
        url=webhook,
    )
    logger.info("Initiated call SID=%s", call.sid)


def main() -> None:
    parser = argparse.ArgumentParser(description="Place a test call to your webhook.")
    parser.add_argument("--to", required=True, help="Destination phone number (E.164).")
    parser.add_argument("--from", dest="from_number", required=False, help="Your Twilio number (E.164).")
    parser.add_argument("--webhook", required=False, help="Webhook URL; defaults to PUBLIC_BASE_URL/voice.")
    args = parser.parse_args()

    from_number = args.from_number or settings.twilio_phone_number
    webhook = args.webhook or (settings.public_base_url and f"{settings.public_base_url}/voice")

    if not from_number:
        logger.error("Provide --from or set TWILIO_PHONE_NUMBER.")
        sys.exit(1)
    if not webhook:
        logger.error("Provide --webhook or set PUBLIC_BASE_URL.")
        sys.exit(1)
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.error("Twilio credentials missing. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.")
        sys.exit(1)

    place_call(args.to, from_number, webhook)


if __name__ == "__main__":
    main()
