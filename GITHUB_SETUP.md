# Run the watcher 24/7 on GitHub Actions (laptop can be off)

This runs the scan every ~5 minutes in GitHub's cloud and pushes to your phone
via ntfy — no computer of yours needs to be on.

## One-time: set up phone push (2 min)
1. Install the **ntfy** app (iOS App Store / Google Play).
2. In the app: **+ → Subscribe to topic** and enter a topic name. Use your own
   secret string, e.g. `amc-odyssey-70mm-ethan-8f3a2c` (anyone who knows the
   topic can send to it, so make it long/unguessable).
3. Remember this topic — you'll paste it into GitHub as a secret below.

## One-time: set up GitHub Actions (~5 min)
1. Create a **new GitHub repo** (private is fine) at https://github.com/new —
   e.g. `amc-odyssey-watch`.
2. Add these two files to it (drag-drop in the web UI works):
   - `amc_odyssey_watch.py`            → repo root
   - `.github/workflows/watch.yml`     → keep this exact path
   (Everything else in this folder is optional/local-only.)
3. Add your ntfy topic as a secret so it isn't public:
   **repo → Settings → Secrets and variables → Actions → New repository secret**
   - Name: `NTFY_TOPIC`
   - Value: your topic from step 2 above
4. Enable Actions if prompted (**Actions** tab → "I understand… enable").
5. Test it now: **Actions tab → "AMC Odyssey 70mm watch" → Run workflow**.
   - Open the run's log; you should see `not available yet — ...` (correct today).
   - To prove the phone alert end-to-end, temporarily change `DATE` in
     `amc_odyssey_watch.py` to a date that already has 70mm showtimes (e.g.
     `2026-07-25`), run the workflow once → you should get a phone push →
     then change `DATE` back to `2026-08-14`.

That's it. From then on it checks every 5 minutes automatically and pushes your
phone the moment Aug 14 IMAX 70mm tickets go live. Tapping the notification
opens the AMC ticket page.

## Notes
- **Fastest possible:** 5 min is GitHub's minimum cron interval, and runs can be
  delayed a few minutes at busy times. That's plenty for a ticket drop.
- **It will ping every 5 min while tickets are available.** Once you've bought,
  stop it: **Actions tab → ⋯ → Disable workflow** (or delete the repo).
- **Keep it alive:** GitHub auto-pauses scheduled workflows after 60 days of no
  repo activity. Irrelevant here (the event is weeks away), but if you extend
  this, just push any commit to reset the clock.
- **Change what it watches:** edit `DATE` / `MOVIE_SLUG` at the top of
  `amc_odyssey_watch.py` and commit.
