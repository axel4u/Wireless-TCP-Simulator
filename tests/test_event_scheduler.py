from simulator.event_scheduler import EventScheduler


def test_events_run_in_time_order_and_stably():
    scheduler = EventScheduler()
    seen = []
    scheduler.schedule(5, lambda: seen.append("later"))
    scheduler.schedule(2, lambda: seen.append("first"))
    scheduler.schedule(2, lambda: seen.append("second"))
    scheduler.run()
    assert seen == ["first", "second", "later"]
    assert scheduler.now_ms == 5
