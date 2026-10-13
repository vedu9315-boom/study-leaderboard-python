
from datetime import datetime

import pytest

from app.sessions import (
    MIN_SECONDS,
    MAX_SECONDS,
    SessionError,
    duration,
    classify,
    split_across_days,
    overlaps,
    rank,
)


def test_duration_normal():
    assert duration(
        datetime(2026, 1, 1, 9),
        datetime(2026, 1, 1, 10),
    ) == 3600


def test_duration_zero():
    t = datetime(2026, 1, 1, 9)
    assert duration(t, t) == 0


def test_duration_end_before_start():
    with pytest.raises(SessionError):
        duration(
            datetime(2026, 1, 1, 10),
            datetime(2026, 1, 1, 9),
        )


def test_classify_short():
    assert classify(MIN_SECONDS - 1) == ("discard", 0)


def test_classify_minimum():
    assert classify(MIN_SECONDS) == ("ok", MIN_SECONDS)


def test_classify_normal():
    assert classify(3600) == ("ok", 3600)


def test_classify_maximum():
    assert classify(MAX_SECONDS) == ("ok", MAX_SECONDS)


def test_classify_excessive():
    assert classify(MAX_SECONDS + 1) == ("capped", MAX_SECONDS)


def test_split_across_midnight():
    start = datetime(2026, 1, 1, 23, 30)
    stop = datetime(2026, 1, 2, 0, 30)

    assert split_across_days(start, stop) == [
        (datetime(2026, 1, 1).date(), 1800),
        (datetime(2026, 1, 2).date(), 1800),
    ]


def test_split_same_day():
    start = datetime(2026, 1, 1, 9)
    stop = datetime(2026, 1, 1, 10)

    assert split_across_days(start, stop) == [
        (start.date(), 3600)
    ]


def test_split_zero_length():
    t = datetime(2026, 1, 1, 9)
    assert split_across_days(t, t) == []


def test_split_end_before_start():
    with pytest.raises(SessionError):
        split_across_days(
            datetime(2026, 1, 1, 10),
            datetime(2026, 1, 1, 9),
        )


def test_overlapping_sessions():
    assert overlaps(
        datetime(2026, 1, 1, 9),
        datetime(2026, 1, 1, 11),
        datetime(2026, 1, 1, 10),
        datetime(2026, 1, 1, 12),
    )


def test_non_overlapping_sessions():
    assert not overlaps(
        datetime(2026, 1, 1, 9),
        datetime(2026, 1, 1, 10),
        datetime(2026, 1, 1, 10),
        datetime(2026, 1, 1, 11),
    )


def test_rank_order():
    assert rank({"Asha": 120, "Bala": 300}) == [
        {"rank": 1, "student": "Bala", "seconds": 300},
        {"rank": 2, "student": "Asha", "seconds": 120},
    ]


def test_rank_tie_alphabetical():
    assert rank({"Ravi": 100, "Anu": 100}) == [
        {"rank": 1, "student": "Anu", "seconds": 100},
        {"rank": 2, "student": "Ravi", "seconds": 100},
    ]


def test_rank_empty():
    assert rank({}) == []
