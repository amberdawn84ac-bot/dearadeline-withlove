"""
Metrics endpoint — /brain/metrics

Exposes in-process counters in Prometheus text format (no external dependency).
Also used by lessons.py to record per-request timing.

Counters reset on process restart (acceptable for Railway — use log aggregation
for long-term trends; this endpoint serves real-time scraping + alerting).
"""
import time
import logging
from collections import deque
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["metrics"])

# ── In-process counters ───────────────────────────────────────────────────────

_counters: dict[str, int] = {
    "canonical_hits_total":   0,
    "canonical_misses_total": 0,
    "lessons_served_total":   0,
}

# Rolling window for average adaptation latency (last 100 requests)
_adaptation_ms_window: deque[float] = deque(maxlen=100)


def record_lesson_served(
    *,
    source: str,          # "canonical" | "orchestrator"
    track: str,
    grade: str,
    adaptation_ms: float | None = None,
    student_id_prefix: str = "unknown",
) -> None:
    """
    Called from lessons.py after each lesson is served.
    Increments counters and emits a structured log line.
    """
    _counters["lessons_served_total"] += 1
    if source == "canonical":
        _counters["canonical_hits_total"] += 1
    else:
        _counters["canonical_misses_total"] += 1

    if adaptation_ms is not None:
        _adaptation_ms_window.append(adaptation_ms)

    logger.info(
        f"[Metrics] event=lesson_served source={source} track={track} "
        f"grade={grade} adaptation_ms={adaptation_ms:.0f} student={student_id_prefix}"
        if adaptation_ms is not None else
        f"[Metrics] event=lesson_served source={source} track={track} "
        f"grade={grade} student={student_id_prefix}"
    )


def _avg_adaptation_ms() -> float:
    if not _adaptation_ms_window:
        return 0.0
    return sum(_adaptation_ms_window) / len(_adaptation_ms_window)


async def _pending_canonical_count() -> int:
    try:
        from app.connections.canonical_store import canonical_store
        pending = await canonical_store.list_pending()
        return len(pending)
    except Exception:
        return -1


@router.get(
    "/brain/metrics",
    response_class=PlainTextResponse,
)
async def metrics() -> PlainTextResponse:
    """
    Prometheus-compatible text exposition of in-process metrics.
    No authentication required (standard practice for /metrics).
    """
    pending = await _pending_canonical_count()
    avg_ms = _avg_adaptation_ms()
    hit_total = _counters["canonical_hits_total"]
    miss_total = _counters["canonical_misses_total"]
    served_total = _counters["lessons_served_total"]
    hit_rate = (hit_total / served_total * 100) if served_total > 0 else 0.0

    lines = [
        "# HELP canonical_hits_total Number of lesson requests served from canonical store",
        "# TYPE canonical_hits_total counter",
        f"canonical_hits_total {hit_total}",
        "",
        "# HELP canonical_misses_total Number of lesson requests that triggered full orchestrator",
        "# TYPE canonical_misses_total counter",
        f"canonical_misses_total {miss_total}",
        "",
        "# HELP lessons_served_total Total lessons served since last process restart",
        "# TYPE lessons_served_total counter",
        f"lessons_served_total {served_total}",
        "",
        "# HELP canonical_hit_rate_percent Canonical hit rate as percentage (rolling since restart)",
        "# TYPE canonical_hit_rate_percent gauge",
        f"canonical_hit_rate_percent {hit_rate:.2f}",
        "",
        "# HELP canonical_pending_count Canonicals currently awaiting admin approval",
        "# TYPE canonical_pending_count gauge",
        f"canonical_pending_count {pending}",
        "",
        "# HELP adaptation_avg_latency_ms Average adaptation latency over last 100 requests (ms)",
        "# TYPE adaptation_avg_latency_ms gauge",
        f"adaptation_avg_latency_ms {avg_ms:.1f}",
        "",
    ]
    return PlainTextResponse("\n".join(lines), media_type="text/plain; version=0.0.4")
