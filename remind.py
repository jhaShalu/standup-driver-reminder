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


def send_reminder(webhook_url, driver):
    message = f"🚀 Reminder: Tomorrow's standup driver is *{driver}*."
    response = requests.post(webhook_url, json={"text": message})
    response.raise_for_status()


def main():
    dry_run = "--dry-run" in sys.argv

    config = load_json(CONFIG_FILE)
    state = load_json(STATE_FILE)

    members = config["members"]
    index = state["index"]
    driver = members[index]

    if dry_run:
        print(f"[DRY RUN] Tomorrow's standup driver would be: {driver}")
    else:
        webhook_url = os.environ.get("GCHAT_WEBHOOK_URL")
        if not webhook_url:
            print("Error: GCHAT_WEBHOOK_URL environment variable is not set.", file=sys.stderr)
            sys.exit(1)
        send_reminder(webhook_url, driver)
        print(f"Reminder sent. Tomorrow's driver: {driver}")

    state["index"] = (index + 1) % len(members)
    save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
