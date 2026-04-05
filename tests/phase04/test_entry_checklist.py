"""ENTRY-05 checklist."""

from datetime import time

from src.entry import validate_pre_entry


def test_entry05_rejects_rr_below_1p5():
    assert not validate_pre_entry(
        entry_price=100.0,
        stop_price=99.0,
        target_price=101.49,
        bias="BULLISH",
        atr20=4.0,
        tick_size=0.25,
        bar_time=time(10, 0),
        session_setup_count=0,
    )


def test_entry05_rejects_sl_tighter_than_4_ticks():
    assert not validate_pre_entry(
        entry_price=100.0,
        stop_price=99.75,
        target_price=102.0,
        bias="BULLISH",
        atr20=10.0,
        tick_size=0.25,
        bar_time=time(10, 0),
        session_setup_count=0,
    )


def test_entry05_rejects_sl_wider_than_1p5_atr20():
    atr20 = 4.0
    risk = 1.51 * atr20
    assert not validate_pre_entry(
        entry_price=100.0,
        stop_price=100.0 - risk,
        target_price=110.0,
        bias="BULLISH",
        atr20=atr20,
        tick_size=0.25,
        bar_time=time(10, 0),
        session_setup_count=0,
    )


def test_entry05_rejects_neutral_bias():
    assert not validate_pre_entry(
        entry_price=100.0,
        stop_price=98.0,
        target_price=105.0,
        bias="NEUTRAL",
        atr20=4.0,
        tick_size=0.25,
        bar_time=time(10, 0),
        session_setup_count=0,
    )


def test_entry05_rejects_after_1545_et():
    assert not validate_pre_entry(
        entry_price=100.0,
        stop_price=98.0,
        target_price=105.0,
        bias="BULLISH",
        atr20=4.0,
        tick_size=0.25,
        bar_time=time(15, 45),
        session_setup_count=0,
    )
    assert not validate_pre_entry(
        entry_price=100.0,
        stop_price=98.0,
        target_price=105.0,
        bias="BULLISH",
        atr20=4.0,
        tick_size=0.25,
        bar_time=time(15, 46),
        session_setup_count=0,
    )


def test_entry05_rejects_when_session_setup_count_ge_3():
    assert not validate_pre_entry(
        entry_price=100.0,
        stop_price=98.0,
        target_price=105.0,
        bias="BULLISH",
        atr20=4.0,
        tick_size=0.25,
        bar_time=time(10, 0),
        session_setup_count=3,
    )
