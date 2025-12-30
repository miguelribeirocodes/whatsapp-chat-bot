import threading
import time as _time
from datetime import datetime, timedelta, timezone
import heapq
import uuid
import logging

logger = logging.getLogger(__name__)

# Timezone do Brasil (GMT-3) - importante para servidor em UTC
BRAZIL_TZ_OFFSET = timedelta(hours=-3)

def agora_brasil() -> datetime:
    """Retorna o horário atual no fuso horário do Brasil (GMT-3)."""
    utc_now = datetime.now(timezone.utc)
    brazil_now = utc_now + BRAZIL_TZ_OFFSET
    return brazil_now.replace(tzinfo=None)

# Min-heap of jobs: (run_at_timestamp, job_id, func, args, kwargs)
_jobs_heap = []
_jobs_lock = threading.Lock()
_stop_event = threading.Event()


def _worker_loop(poll_interval=30):
    logger.info("[scheduler] Worker started")
    while not _stop_event.is_set():
        now_ts = agora_brasil().timestamp()  # Usa horário do Brasil
        to_run = []
        with _jobs_lock:
            while _jobs_heap and _jobs_heap[0][0] <= now_ts:
                item = heapq.heappop(_jobs_heap)
                to_run.append(item)
        for run_at_ts, job_id, func, args, kwargs in to_run:
            try:
                logger.info("[scheduler] Running job %s scheduled for %s", job_id, datetime.fromtimestamp(run_at_ts))
                func(*args, **(kwargs or {}))
            except Exception:
                logger.exception("[scheduler] Exception executing job %s", job_id)
        _time.sleep(poll_interval)


_worker_thread = None


def start(poll_interval=30):
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_worker_loop, args=(poll_interval,), daemon=True)
    _worker_thread.start()


def stop():
    _stop_event.set()


def schedule_at(run_at: datetime, func, *args, **kwargs) -> str:
    """Schedule func to run at specific datetime. Returns job id."""
    run_ts = run_at.timestamp()
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        heapq.heappush(_jobs_heap, (run_ts, job_id, func, args, kwargs))
    logger.info("[scheduler] Scheduled job %s at %s", job_id, run_at)
    return job_id


def schedule_in(seconds: float, func, *args, **kwargs) -> str:
    return schedule_at(agora_brasil() + timedelta(seconds=seconds), func, *args, **kwargs)


def schedule_daily(hour: int, minute: int, func, *args, **kwargs) -> str:
    """Schedule a job that will run every day at hour:minute (Brasil GMT-3). Returns id of first scheduled run."""
    now = agora_brasil()  # Usa horário do Brasil
    run_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_today <= now:
        run_today = run_today + timedelta(days=1)

    def _runner_and_reschedule(*a, **k):
        try:
            func(*a, **k)
        except Exception:
            logger.exception("[scheduler] daily job exception")
        # schedule next day (Brasil time)
        schedule_at(agora_brasil().replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=1), _runner_and_reschedule, *a, **k)

    return schedule_at(run_today, _runner_and_reschedule, *args, **kwargs)


# Start worker automatically when module is imported
start()
