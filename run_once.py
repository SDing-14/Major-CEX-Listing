"""
CI entrypoint - runs a single scrape -> process -> database cycle and exits.

main.py's own `schedule` loop is meant for a long-running local process; it
isn't a fit for GitHub Actions, where the workflow's own cron trigger handles
scheduling and each run should just do one pass and exit. This wraps
ListingTracker.run_full_cycle() for that purpose and prints a small summary
GitHub Actions can surface in the job log.
"""
from main import ListingTracker


def main():
    tracker = ListingTracker(headless=True)
    tracker.run_full_cycle()


if __name__ == "__main__":
    main()
