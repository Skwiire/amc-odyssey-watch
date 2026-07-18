#!/usr/bin/env python3
"""
AMC Lincoln Square 13 — "The Odyssey – IMAX 70mm Event" ticket watcher.

Polls the AMC showtimes page for a specific date + the IMAX 70mm event and
alerts (macOS notification + spoken voice + sound + opens the page) the moment
buyable showtimes appear.

Detection is based on AMC's *movie-scoped* showtimes URL, which does real
server-side filtering. When the event has no showtimes for the date, the page
says "no showtimes found" and contains zero `/showtimes/<id>` purchase links.
When tickets go live, those links appear.

Stdlib only — no pip installs. macOS only for the alert bits.

Usage:
    python3 amc_odyssey_watch.py             # loop forever, check every 5 min
    python3 amc_odyssey_watch.py --once      # single check (used by launchd)
    python3 amc_odyssey_watch.py --interval 180   # loop every 3 min
    python3 amc_odyssey_watch.py --test-alert      # fire the alert now, to verify it works
"""

import argparse
import gzip
import io
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

# ---------------------------------------------------------------------------
# CONFIG — change the date/movie here if you want to watch something else.
# ---------------------------------------------------------------------------
DATE = "2026-08-14"                       # Friday, Aug 14 2026
MOVIE_SLUG = "the-odyssey-80679"          # "The Odyssey – IMAX 70mm Event" at Lincoln Sq
MOVIE_LABEL = "The Odyssey – IMAX 70mm Event"
THEATRE = "AMC Lincoln Square 13"
BASE = ("https://www.amctheatres.com/movie-theatres/new-york-city/"
        "amc-lincoln-square-13/showtimes")
WATCH_URL = f"{BASE}?date={DATE}&movie={MOVIE_SLUG}"

# --- Phone push via ntfy.sh (free, no account) --------------------------------
# Install the "ntfy" app on your phone, then subscribe to this exact topic.
# Anyone who knows the topic can publish to it, so keep it long & secret.
# Override at runtime with:  NTFY_TOPIC=your-topic python3 amc_odyssey_watch.py
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "amc-odyssey-70mm-ethan-8f3a2c")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

# Interval + politeness
DEFAULT_INTERVAL = 300                    # seconds between checks (loop mode)
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/126.0.0.0 Safari/537.36")

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(HERE, "watch.log")
FOUND_FLAG = os.path.join(HERE, "FOUND")   # created once tickets are detected


def log(msg: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def fetch(url: str, timeout: int = 30) -> tuple[int, str]:
    """GET a URL, following redirects, returning (status, decoded_text)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip",
    })

    def _decode(resp_or_err) -> str:
        raw = resp_or_err.read()
        if resp_or_err.headers.get("Content-Encoding") == "gzip":
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        return raw.decode("utf-8", errors="ignore")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, _decode(resp)
    except urllib.error.HTTPError as e:
        # e.g. 429 = Cloudflare 1015 rate limit. Return the code instead of
        # raising so check() can classify it (and never false-alarm on it).
        try:
            return e.code, _decode(e)
        except Exception:  # noqa: BLE001
            return e.code, ""


def check() -> tuple[bool, list[str], str]:
    """
    Return (available, showtime_ids, reason).
    available == True means buyable IMAX 70mm showtimes exist for the date.
    """
    status, html = fetch(WATCH_URL)

    # Guard against Cloudflare rate-limit / challenge pages — never false-alarm.
    low = html.lower()
    if status == 429 or "error 1015" in low or "you are being rate limited" in low:
        return False, [], "Cloudflare rate-limited this run (429/1015) — retrying next cycle"
    if status != 200 or "just a moment" in low or "attention required" in low:
        return False, [], f"non-content response (status {status}, possible bot-check)"

    showtime_ids = sorted(set(re.findall(r"/showtimes/(\d+)", html)))
    no_showtimes = "no showtimes found" in low

    # Available = the scoped page actually lists purchasable showtimes.
    if showtime_ids and not no_showtimes:
        return True, showtime_ids, f"{len(showtime_ids)} showtime(s) live"
    if no_showtimes:
        return False, [], "not yet on sale (\"no showtimes found\")"
    return False, [], "no showtime links present"


# ---------------------------------------------------------------------------
# macOS alerting
# ---------------------------------------------------------------------------
def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=False, timeout=20)
    except Exception as e:  # noqa: BLE001
        log(f"alert subcommand failed ({cmd[0]}): {e}")


def push_phone(title: str, message: str, click_url: str) -> None:
    """Send a push notification to your phone via ntfy.sh (works from anywhere,
    including cloud hosts). Fails quietly if offline."""
    # HTTP header values must be latin-1; strip emoji/non-ASCII from the title.
    ascii_title = title.encode("ascii", "ignore").decode().strip() or "AMC ticket alert"
    try:
        req = urllib.request.Request(
            NTFY_URL,
            data=message.encode("utf-8"),   # body is UTF-8, emoji OK here
            method="POST",
            headers={
                "Title": ascii_title,
                "Priority": "urgent",
                "Tags": "ticket,clapper",
                "Click": click_url,
            },
        )
        urllib.request.urlopen(req, timeout=15).read()
        log(f"    phone push sent to ntfy topic '{NTFY_TOPIC}'")
    except Exception as e:  # noqa: BLE001
        log(f"    phone push failed: {e}")


def notify(title: str, message: str) -> None:
    # Persistent-ish banner + default sound.
    script = (f'display notification "{message}" with title "{title}" '
              f'sound name "Glass"')
    _run(["osascript", "-e", script])


def alert(showtime_ids: list[str], open_browser: bool) -> None:
    n = len(showtime_ids)
    title = "🎟️ ODYSSEY 70mm TICKETS LIVE"
    msg = f"{THEATRE} — {DATE}: {n} IMAX 70mm showtime(s) now on sale!"
    log(f"*** ALERT *** {msg}")
    log(f"    Buy: {WATCH_URL}")
    for sid in showtime_ids:
        log(f"    showtime: https://www.amctheatres.com/showtimes/{sid}")

    # 0) Phone push (works even when this runs in the cloud)
    push_phone(title, msg + f"  ▶ {WATCH_URL}", WATCH_URL)
    # 1) Notification banner (local Mac only; harmless no-op in the cloud)
    notify(title, msg)
    # 2) Spoken alert (hard to miss)
    _run(["say", "-v", "Samantha",
          "Attention. Odyssey 70 millimeter I-MAX tickets are now on sale at Lincoln Square."])
    # 3) Audible chime a few times
    for _ in range(3):
        _run(["afplay", "/System/Library/Sounds/Glass.aiff"])
    # 4) Open the purchase page once (guarded by FOUND flag by caller)
    if open_browser:
        _run(["open", WATCH_URL])


def already_found() -> bool:
    return os.path.exists(FOUND_FLAG)


def mark_found(showtime_ids: list[str]) -> None:
    try:
        with open(FOUND_FLAG, "w") as f:
            f.write(f"{datetime.now().isoformat()}\n{WATCH_URL}\n")
            f.write("\n".join(showtime_ids) + "\n")
    except OSError:
        pass


def run_once(open_browser_first_time: bool = True) -> bool:
    """One check. Alert if available. Returns True if available."""
    try:
        available, ids, reason = check()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log(f"check failed (will retry next cycle): {e}")
        return False

    if available:
        first = not already_found()
        alert(ids, open_browser=open_browser_first_time and first)
        if first:
            mark_found(ids)
        return True

    log(f"not available yet — {reason}")
    return False


def main() -> int:
    p = argparse.ArgumentParser(description="Watch AMC for Odyssey 70mm IMAX tickets.")
    p.add_argument("--once", action="store_true",
                   help="run a single check and exit (for launchd/cron).")
    p.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                   help=f"seconds between checks in loop mode (default {DEFAULT_INTERVAL}).")
    p.add_argument("--test-alert", action="store_true",
                   help="fire the alert immediately to confirm it works, then exit.")
    args = p.parse_args()

    if args.test_alert:
        log("firing TEST alert…")
        alert(["000000"], open_browser=False)
        return 0

    log(f"watching: {MOVIE_LABEL}")
    log(f"theatre : {THEATRE}")
    log(f"date    : {DATE}")
    log(f"url     : {WATCH_URL}")

    if args.once:
        run_once()
        return 0

    log(f"loop mode — checking every {args.interval}s (Ctrl-C to stop).")
    while True:
        found = run_once()
        # keep re-alerting while available so you don't miss it; only the
        # browser opens once (guarded by FOUND flag).
        sleep_for = max(30, args.interval)
        time.sleep(sleep_for)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("stopped by user.")
        sys.exit(0)
