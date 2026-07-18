# AMC Odyssey 70mm IMAX ticket watcher

Watches **AMC Lincoln Square 13** for **"The Odyssey – IMAX 70mm Event"** on
**Thursday, August 13, 2026** and alerts you the moment tickets go on sale.

## How it detects availability
It requests AMC's *movie-scoped* showtimes URL:
```
https://www.amctheatres.com/movie-theatres/new-york-city/amc-lincoln-square-13/showtimes?date=2026-08-13&movie=the-odyssey-80679
```
AMC filters this server-side to just the 70mm event. Today it returns
"no showtimes found" with zero purchase links. When tickets go live, the page
lists `/showtimes/<id>` links — that's the trigger.

## When it alerts, you get
- a macOS notification banner,
- a spoken voice alert,
- three chimes,
- the ticket page auto-opens in your browser (once).

## Two ways to run it

### A) Quick — run in a Terminal (stops when you close the window)
```bash
python3 ~/amc-odyssey-watch/amc_odyssey_watch.py            # every 5 min
python3 ~/amc-odyssey-watch/amc_odyssey_watch.py --interval 180   # every 3 min
```

### B) Always-on — load the LaunchAgent (survives reboots, runs in background)
```bash
cp ~/amc-odyssey-watch/com.ethan.amc-odyssey-watch.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.ethan.amc-odyssey-watch.plist
```
It then runs a check every 5 minutes while you're logged in.

To stop it:
```bash
launchctl unload ~/Library/LaunchAgents/com.ethan.amc-odyssey-watch.plist
```

## Useful commands
```bash
# test the alert right now
python3 ~/amc-odyssey-watch/amc_odyssey_watch.py --test-alert

# one manual check
python3 ~/amc-odyssey-watch/amc_odyssey_watch.py --once

# watch the log
tail -f ~/amc-odyssey-watch/watch.log
```

## Notes / tuning
- AMC says *"Showtimes for Friday and beyond are usually posted by Wednesday
  afternoon,"* so Aug 13 showtimes will likely post the week before — but big
  IMAX 70mm events sometimes go on sale in an earlier special batch, which is
  why constant scanning is worth it.
- 5-minute polling is polite (~288 requests/day) and plenty fast. Don't go
  below ~60s.
- Once found, a `FOUND` file is written so the browser only auto-opens once;
  notifications keep firing every cycle until you stop the watcher. Delete
  `FOUND` to reset.
- To watch a **different date**, edit `DATE` near the top of
  `amc_odyssey_watch.py`. For a different movie/theatre, update `MOVIE_SLUG`
  and `BASE`.
