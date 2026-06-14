import datetime
import json
import os
import sys
from pathlib import Path

import requests

CONFIG_FILE = Path(__file__).parent / "config.json"
STATE_FILE = Path(__file__).parent / "state.json"
HISTORY_FILE = Path(__file__).parent / "history.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def send_reminder(webhook_url, driver, secondary, standup_date, upcoming):
    upcoming_str = " → ".join(upcoming)
    message = (
        f"[{standup_date}]\n"
        f"Heads up, team! *{driver}* is at the wheel for standup. See you there! | Backup: *{secondary}*\n\n"
        f"📅 Upcoming: {upcoming_str}"
    )
    response = requests.post(webhook_url, json={"text": message})
    if not response.ok:
        print(f"HTTP {response.status_code} — {response.text}", file=sys.stderr)
        response.raise_for_status()


def main():
    dry_run = "--dry-run" in sys.argv
    show_rotation = "--show-rotation" in sys.argv
    skip_names = [sys.argv[i + 1] for i, arg in enumerate(sys.argv) if arg == "--skip" and i + 1 < len(sys.argv)]

    config = load_json(CONFIG_FILE)
    state = load_json(STATE_FILE)

    members = config["members"]
    index = state["index"]

    if show_rotation:
        driver = members[index]
        upcoming_count = config.get("upcoming_count", 5)
        upcoming = [members[(index + i) % len(members)] for i in range(1, upcoming_count + 1)]
        print(f"Current driver: {driver}")
        print(f"📅 Upcoming:     {' → '.join(upcoming)}")
        return

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    if tomorrow.weekday() >= 5:
        print(f"Skipping: {tomorrow.strftime('%A, %B %d')} is a weekend.")
        return

    holidays = config.get("holidays", [])
    if tomorrow.strftime("%Y-%m-%d") in holidays:
        print(f"Skipping: {tomorrow.strftime('%B %-d, %Y')} is a holiday.")
        return

    # Find actual driver, skipping anyone on leave (deferred — they drive next time)
    actual_index = index
    for _ in range(len(members)):
        if members[actual_index] not in skip_names:
            break
        actual_index = (actual_index + 1) % len(members)
    else:
        print("Error: all members are skipped.", file=sys.stderr)
        sys.exit(1)

    driver = members[actual_index]
    secondary = members[(actual_index + 1) % len(members)]
    standup_date = f"{tomorrow.strftime('%B')} {tomorrow.day}, {tomorrow.year}"
    upcoming_count = config.get("upcoming_count", 5)
    upcoming = [members[(actual_index + i) % len(members)] for i in range(1, upcoming_count + 1)]

    if dry_run:
        upcoming_str = " → ".join(upcoming)
        print(
            f"[DRY RUN] [{standup_date}]\n"
            f"Heads up, team! *{driver}* is at the wheel for standup. See you there! | Backup: *{secondary}*\n\n"
            f"📅 Upcoming: {upcoming_str}"
        )
    else:
        webhook_url = os.environ.get("GCHAT_WEBHOOK_URL")
        if not webhook_url:
            print("Error: GCHAT_WEBHOOK_URL environment variable is not set.", file=sys.stderr)
            sys.exit(1)
        send_reminder(webhook_url, driver, secondary, standup_date, upcoming)
        print(f"Reminder sent. Driver: {driver} | Backup: {secondary} | Date: {standup_date}")
        history = load_json(HISTORY_FILE) if HISTORY_FILE.exists() else []
        history.append({"date": standup_date, "driver": driver, "backup": secondary})
        save_json(HISTORY_FILE, history)

    if not dry_run:
        # If someone was skipped, keep index at the deferred person so they drive next time
        next_index = index if actual_index != index else (index + 1) % len(members)
        state["index"] = next_index
        save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
