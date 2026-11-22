Larkspur Docs · version 3.2

# Changelog

## 3.2.1 (18 March 2026)

- The sweeper no longer removes jobs that are still running when their heartbeat is late by less than
  one poll interval.
- `larkspur pause` now refuses unknown queue names instead of creating them.

## 3.2.0 (4 March 2026)

- Heartbeats for running jobs, and the `dead` state for jobs that used up their attempts.
- The drain timeout for workers that are asked to stop.
- Signed jobs with HMAC-SHA256 when `signing_key` is set.

## 3.1.0 (12 November 2025)

- Periodic jobs with cron expressions.
- The dashboard shows the age of the oldest waiting job per queue.

Edit this page on the Larkspur wiki · Larkspur contributors
