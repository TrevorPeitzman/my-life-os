#!/usr/bin/env python3
"""Morning push notification + daily file seeding. Run at ~07:00 via cron."""
import sys
from pathlib import Path

# Allow importing app modules when run as a script inside the container
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.services import push_service, vault


def main() -> None:
    tz = ZoneInfo(settings.TZ)
    today = datetime.now(tz).date().isoformat()

    # Ensure today's daily note exists (creates from template if absent)
    vault.read_note("daily", today)
    print(f"[morning_push] Daily note ready: {today}")

    # Count open tasks for the notification body
    open_tasks = vault.get_open_tasks(horizon="daily", days_back=7)
    task_count = len(open_tasks)

    payload = {
        "title": "Good morning! Time to plan your day",
        "body": f"{task_count} open task{'s' if task_count != 1 else ''} waiting. Tap to start your morning check-in.",
        "url": "/journal-morning.html",
        "icon": "/icon-192.png",
    }

    results = push_service.send_push_to_all(payload)
    print(
        f"[morning_push] Notifications: sent={results['sent']} "
        f"failed={results['failed']} removed={results['removed']}"
    )


if __name__ == "__main__":
    main()
