from datetime import datetime
from zoneinfo import ZoneInfo


def should_run_now(skip_guard: bool, now: datetime | None = None) -> bool:
    if skip_guard:
        return True
    now_paris = now.astimezone(ZoneInfo("Europe/Paris")) if now else datetime.now(ZoneInfo("Europe/Paris"))
    return now_paris.minute == 0 and now_paris.hour in {0, 1}
