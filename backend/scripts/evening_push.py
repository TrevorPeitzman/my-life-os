#!/usr/bin/env python3
"""Evening push notification + tomorrow's file seeding. Run at ~20:00 via cron."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import settings
from app.services import push_service, vault


def main() -> None:
    tz = ZoneInfo(settings.TZ)
    today = datetime.now(tz).date()
    tomorrow = today + timedelta(days=1)

    today_str = today.isoformat()
    tomorrow_str = tomorrow.isoformat()

    # Ensure today's note exists (should already, but belt-and-suspenders)
    vault.read_note("daily", today_str)

    # Seed tomorrow's note so it's ready for the morning
    if not vault.note_exists("daily", tomorrow_str):
        vault.read_note("daily", tomorrow_str)
        print(f"[evening_push] Seeded tomorrow's note: {tomorrow_str}")
    else:
        print(f"[evening_push] Tomorrow's note already exists: {tomorrow_str}")

    payload = {
        "title": "Evening reflection time",
        "body": "How did today go? Take 5 minutes to wrap up and set tomorrow's intentions.",
        "url": "/journal-evening.html",
        "icon": "/icon-192.png",
    }

    results = push_service.send_push_to_all(payload)
    print(
        f"[evening_push] Notifications: sent={results['sent']} "
        f"failed={results['failed']} removed={results['removed']}"
    )


if __name__ == "__main__":
    main()
