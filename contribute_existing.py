import argparse
import os
import re
import sys
from datetime import datetime, timedelta
from random import randint
from subprocess import Popen


def main(def_args=sys.argv[1:]):
    args = arguments(def_args)
    curr_date = datetime.now()

    no_weekends = args.no_weekends
    frequency = args.frequency

    # Ensure assets directory exists
    os.makedirs('assets', exist_ok=True)

    # Auto-detect how many days to backfill based on last entry in activity.log
    days_before = get_days_since_last_run(args.days_before)

    if days_before < 0:
        sys.exit('days_before must not be negative')

    days_after = args.days_after
    if days_after < 0:
        sys.exit('days_after must not be negative')

    start_date = curr_date.replace(hour=20, minute=0, second=0, microsecond=0) - timedelta(days_before)
    total_commits = 0

    print(f"Generating contributions starting from {start_date.strftime('%Y-%m-%d')} ({days_before} day(s) to backfill)...")

    for day in (start_date + timedelta(n) for n in range(days_before + days_after + 1)):
        if day.date() > curr_date.date():
            break  # don't commit future dates
        if (not no_weekends or day.weekday() < 5) and randint(0, 100) < frequency:
            for commit_time in (day + timedelta(minutes=m) for m in range(contributions_per_day(args))):
                contribute(commit_time)
                total_commits += 1

    if total_commits == 0:
        print("No commits needed — already up to date.")
        return

    print(f"Generated {total_commits} commits locally.")

    # Push only if --push flag is set (used when running locally, not via GitHub Actions)
    if args.push:
        print("Pushing to GitHub remote repository...")
        run(['git', 'push', 'origin', 'main'])
        print('\nRepository generation completed successfully!')
    else:
        print("Skipping push (handled externally or by CI).")


def get_days_since_last_run(default_days):
    """Read activity.log and calculate how many days have passed since the last entry."""
    log_path = os.path.join(os.getcwd(), 'assets', 'activity.log')
    if not os.path.exists(log_path):
        return default_days

    last_date = None
    pattern = re.compile(r'Contribution: (\d{4}-\d{2}-\d{2})')

    try:
        with open(log_path, 'r') as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    last_date = datetime.strptime(m.group(1), '%Y-%m-%d').date()
    except Exception:
        return default_days

    if last_date is None:
        return default_days

    today = datetime.now().date()
    missed = (today - last_date).days
    print(f"Last contribution was on {last_date}. Missed {missed} day(s).")
    # Cap at 365 to avoid going overboard after long offline periods
    return min(missed, 365)


def contribute(date):
    date_str = date.strftime('%Y-%m-%d %H:%M:%S')
    log_path = os.path.join(os.getcwd(), 'assets', 'activity.log')
    with open(log_path, 'a') as file:
        file.write(date.strftime('Contribution: %Y-%m-%d %H:%M') + '\n')
    run(['git', 'add', 'assets/activity.log'])
    env = os.environ.copy()
    env['GIT_COMMITTER_DATE'] = date_str
    run(['git', 'commit', '-m', f"Activity Log: {date.strftime('%Y-%m-%d %H:%M')}",
         '--date', date_str], env=env)


def run(commands, env=None):
    Popen(commands, env=env).wait()


def contributions_per_day(args):
    max_c = args.max_commits
    if max_c > 20:
        max_c = 20
    if max_c < 1:
        max_c = 1
    return randint(1, max_c)


def arguments(argsval):
    parser = argparse.ArgumentParser()
    parser.add_argument('-nw', '--no_weekends', required=False, action='store_true', default=False)
    parser.add_argument('-mc', '--max_commits', type=int, default=6, required=False)
    parser.add_argument('-fr', '--frequency', type=int, default=90, required=False)
    parser.add_argument('-db', '--days_before', type=int, default=1, required=False,
                        help='Fallback days_before if activity.log has no entries')
    parser.add_argument('-da', '--days_after', type=int, default=0, required=False)
    parser.add_argument('-p', '--push', required=False, action='store_true', default=False,
                        help='Push to remote after committing (use when running locally)')
    return parser.parse_args(argsval)


if __name__ == "__main__":
    main()
