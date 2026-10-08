"""Pure session rules. No database, no HTTP."""
from datetime import timedelta

MIN_SECONDS = 60             # under a minute is a misclick
MAX_SECONDS = 6 * 60 * 60    # nobody studies more than six hours unbroken


class SessionError(ValueError):
    pass


def duration(started, stopped):
    if stopped < started:
        raise SessionError("a session cannot end before it began")
    return int((stopped - started).total_seconds())


def classify(seconds):
    """Decide what to do with a session of this length."""
    if seconds < MIN_SECONDS:
        return "discard", 0
    if seconds > MAX_SECONDS:
        # Somebody left the timer running. Keep the plausible part rather
        # than throwing the whole thing away or crediting six hours of sleep.
        return "capped", MAX_SECONDS
    return "ok", seconds


def split_across_days(started, stopped):
    """Split a session that crosses midnight, so daily totals stay honest.

    Returns [(date, seconds), ...]. A session from 23:30 to 00:30 counts
    30 minutes against each day, not an hour against one.
    """
    if stopped < started:
        raise SessionError("a session cannot end before it began")
    out = []
    cursor = started
    while cursor.date() < stopped.date():
        midnight = (cursor + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0)
        out.append((cursor.date(), int((midnight - cursor).total_seconds())))
        cursor = midnight
    out.append((cursor.date(), int((stopped - cursor).total_seconds())))
    return [(d, s) for d, s in out if s > 0]


def overlaps(a_start, a_stop, b_start, b_stop):
    """Two sessions by the same student must not overlap."""
    return a_start < b_stop and b_start < a_stop


def rank(totals):
    """Totals is {student: seconds}. Ties break alphabetically so the
    order is stable between page loads."""
    return [{"rank": i + 1, "student": s, "seconds": v}
            for i, (s, v) in enumerate(
                sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])))]
