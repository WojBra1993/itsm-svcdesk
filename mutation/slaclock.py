# ai-generated: 100% - Claude Code (Opus 5.5) wrote this file from design/LAB5.md section 8; the lecturer reviews it
"""slaclock - the SLA arithmetic of a service desk, as pure functions (ITSM 2026, Lab 5, Stretch 1).

Every datetime is naive and on one local calendar. The module works at minute resolution: the seconds and
microseconds of every datetime argument are ignored. Business hours are Monday to Friday, the half-open window
[08:00, 16:00); there are no public holidays. Durations and targets are whole minutes (int).
"""

import re
from datetime import datetime, timedelta

OPENING = 8 * 60            # 08:00, in minutes after midnight
CLOSING = 16 * 60           # 16:00
MAX_DAYS = 366              # the longest calendar span the business-hours functions accept
WARNING_PERCENT = 75        # an SLA clock is in "warning" from this share of its target on
TARGETS = {"P1": (15, 240), "P2": (60, 480), "P3": (240, 1440), "P4": (480, 4320)}
_DURATION = re.compile(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?")
_MINUTE = timedelta(minutes=1)


def priority_of(impact: int, urgency: int, vip: bool = False) -> str:
    """The priority of a ticket, "P1" (most urgent) to "P4".

    impact and urgency are each an int from 1 (high) to 3 (low); anything else (0, 4, 2.0, True, "1") raises
    ValueError. The matrix: impact + urgency - 1, capped at 4 - so (1, 1) is P1, (1, 2) and (2, 1) are P2,
    (1, 3), (2, 2) and (3, 1) are P3, and the three other cells are P4. A VIP ticket is never below P2: when vip is
    true, P3 and P4 become P2, and P1 and P2 are unchanged.
    """
    for value in (impact, urgency):
        if type(value) is not int or not 1 <= value <= 3:
            raise ValueError(f"impact and urgency must be integers from 1 to 3, got {value!r}")
    level = min(impact + urgency - 1, 4)
    if vip and level > 2:
        level = 2
    return f"P{level}"


def targets(priority: str) -> tuple[int, int]:
    """The (response, resolution) targets of a priority, in minutes: P1 (15, 240), P2 (60, 480), P3 (240, 1440),
    P4 (480, 4320). The lookup is exact: any other string ("p1", " P1", "P5") raises ValueError."""
    if priority not in TARGETS:
        raise ValueError(f"unknown priority {priority!r}")
    return TARGETS[priority]


def sla_state(elapsed: int, target: int) -> str:
    """The state of an SLA clock that has run `elapsed` minutes against a target of `target` minutes.

    "breached" when elapsed > target (as in svcdesk, equality is not a breach: at exactly 100 % the clock is in
    "warning"); otherwise "warning" when elapsed is at least WARNING_PERCENT (75) % of target; otherwise "ok". No
    rounding: for a target of 15 the warning starts at 11.25 minutes, so 11 is "ok", 12 is "warning", 15 is still
    "warning" and 16 is "breached". elapsed < 0 or target <= 0 raises ValueError.
    """
    if elapsed < 0 or target <= 0:
        raise ValueError("elapsed must be at least 0 and target above 0")
    if elapsed > target:
        return "breached"
    if elapsed * 100 >= target * WARNING_PERCENT:
        return "warning"
    return "ok"


def is_business_time(moment: datetime) -> bool:
    """True when `moment` is inside business hours: Monday to Friday, from 08:00 inclusive to 16:00 exclusive
    (07:59 and 16:00 are outside, 08:00 and 15:59 are inside)."""
    minute = moment.hour * 60 + moment.minute
    return moment.weekday() < 5 and OPENING <= minute < CLOSING


def add_business_minutes(start: datetime, minutes: int) -> datetime:
    """The instant at which `minutes` business minutes have run after `start`: the due date of a paused SLA clock.

    A start outside business hours first moves to the next opening (08:00 of the same day when before opening, else
    of the next business day); the minutes are then consumed from consecutive business windows. A target that ends
    exactly at closing is due at 16:00 that day, not at 08:00 of the next business day. Zero minutes give the start
    itself when it is inside business hours, else the next opening. minutes < 0 raises ValueError, and so does a due
    date more than MAX_DAYS calendar days after the start's date.
    """
    if minutes < 0:
        raise ValueError("minutes must not be negative")
    start = start.replace(second=0, microsecond=0)
    midnight = start.replace(hour=0, minute=0)
    for offset in range(MAX_DAYS + 1):
        day = midnight + timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        begin = max(start, day + timedelta(minutes=OPENING))
        available = (day + timedelta(minutes=CLOSING) - begin) // _MINUTE
        if available <= 0:
            continue
        if minutes <= available:
            return begin + minutes * _MINUTE
        minutes -= available
    raise ValueError(f"the due date is more than {MAX_DAYS} days after the start")


def business_minutes_between(start: datetime, end: datetime) -> int:
    """The business minutes in the half-open interval [start, end): how long an SLA clock that pauses outside
    business hours has run. start == end gives 0; end before start raises ValueError, and so do dates more than
    MAX_DAYS calendar days apart. For every valid start and minutes,
    business_minutes_between(start, add_business_minutes(start, minutes)) == minutes."""
    start = start.replace(second=0, microsecond=0)
    end = end.replace(second=0, microsecond=0)
    if end < start:
        raise ValueError("end is before start")
    first = start.replace(hour=0, minute=0)
    span = (end.replace(hour=0, minute=0) - first).days
    if span > MAX_DAYS:
        raise ValueError(f"start and end are more than {MAX_DAYS} days apart")
    return sum(_window(first + timedelta(days=offset), start, end) for offset in range(span + 1))


def _window(day: datetime, start: datetime, end: datetime) -> int:
    """The business minutes of [start, end) that fall on `day` (a midnight)."""
    if day.weekday() >= 5:
        return 0
    begin = max(start, day + timedelta(minutes=OPENING))
    finish = min(end, day + timedelta(minutes=CLOSING))
    return max(0, (finish - begin) // _MINUTE)


def escalation_tier(priority: str, breached: bool, reopens: int) -> int:
    """Who owns a ticket now: 0 the service desk, 1 the team lead, 2 the service owner, 3 the duty manager.

    P1 and P2 start at 1, P3 and P4 at 0. A breached SLA adds 1, and 1 more for a P1; a ticket reopened at least
    twice (reopens >= 2) adds 1. The result is at most 3. An unknown priority (as targets() decides) or reopens < 0
    raises ValueError.
    """
    if priority not in TARGETS or reopens < 0:
        raise ValueError(f"cannot escalate priority {priority!r} with {reopens!r} reopens")
    tier = 1 if priority in ("P1", "P2") else 0
    if breached:
        tier += 1
        if priority == "P1":
            tier += 1
    if reopens >= 2:
        tier += 1
    return min(tier, 3)


def parse_duration(text: str) -> int:
    """The minutes in a duration written as days, hours and minutes, in that order, each at most once: "90m",
    "4h", "1h30m", "2d", "1d4h", "1d0h5m". Surrounding whitespace is ignored; units are lower case; nothing may
    stand between the parts. When the days or the hours are not zero, the minutes must be below 60 ("1h59m" is 119,
    "1h60m" is an error, "60m" and "0h60m" are 60). The result must be positive. Anything else ("", "0m", "1.5h",
    "30m1h", "-5m", "1 h") raises ValueError.
    """
    match = _DURATION.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"not a duration: {text!r}")
    days, hours, minutes = (int(part) if part else 0 for part in match.groups())
    if (days or hours) and minutes >= 60:
        raise ValueError(f"minutes must be below 60 after days or hours: {text!r}")
    total = days * 1440 + hours * 60 + minutes
    if total <= 0:
        raise ValueError(f"not a positive duration: {text!r}")
    return total
