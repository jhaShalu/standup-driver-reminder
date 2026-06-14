import datetime
import json
import os
import sys
from pathlib import Path

import requests

CONFIG_FILE = Path(__file__).parent / "config.json"
STATE_FILE = Path(__file__).parent / "state.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def send_reminder(webhook_url, driver, secondary, standup_date):
    message = f"[{standup_date}]\nHeads up, team! *{driver}* is at the wheel for standup. See you there! | Backup: *{secondary}*"
    response = requests.post(webhook_url, json={"text": message})
    if not response.ok:
        print(f"HTTP {response.status_code} — {response.text}", file=sys.stderr)
        response.raise_for_status()


def main():
    dry_run = "--dry-run" in sys.argv

    config = load_json(CONFIG_FILE)
    state = load_json(STATE_FILE)

    members = config["members"]
    index = state["index"]

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    if tomorrow.weekday() >= 5:
        print(f"Skipping: {tomorrow.strftime('%A, %B %d')} is a weekend.")
        return

    driver = members[index]
    secondary = members[(index + 1) % len(members)]
    standup_date = f"{tomorrow.strftime('%B')} {tomorrow.day}, {tomorrow.year}"

    if dry_run:
        print(f"[DRY RUN] [{standup_date}]\nHeads up, team! *{driver}* is at the wheel for standup. See you there! | Backup: *{secondary}*")
    else:
        webhook_url = os.environ.get("GCHAT_WEBHOOK_URL")
        if not webhook_url:
            print("Error: GCHAT_WEBHOOK_URL environment variable is not set.", file=sys.stderr)
            sys.exit(1)
        send_reminder(webhook_url, driver, secondary, standup_date)
        print(f"Reminder sent. Driver: {driver} | Backup: {secondary} | Date: {standup_date}")

    if not dry_run:
        state["index"] = (index + 1) % len(members)
        save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
