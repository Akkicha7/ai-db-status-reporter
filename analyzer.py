"""
analyzer.py
───────────
Rule-based health analyzer.

Takes the raw metrics dict from metrics_collector.collect() and produces:
  - A list of structured findings (each with severity, metric, message)
  - An overall status  (OK / WARNING / CRITICAL)
  - A composite health score (0–100)
  - A delta comparison dict when a previous snapshot is provided

Entry point:
    analyze(metrics, previous_metrics=None) -> AnalysisResult
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import config

logger = logging.getLogger(__name__)

# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Finding:
    severity: str          # "OK" | "WARNING" | "CRITICAL"
    metric: str            # e.g. "connection_pct"
    value: Any             # actual measured value
    threshold: Any         # the threshold that was crossed
    message: str           # human-readable description
    emoji: str = "ℹ️"


@dataclass
class AnalysisResult:
    overall_status: str              # "OK" | "WARNING" | "CRITICAL"
    health_score: int                # 0–100
    findings: list[Finding]          # all evaluated findings
    issues: list[Finding]            # only WARNING / CRITICAL
    deltas: dict[str, float]         # metric changes vs previous run
    metrics: dict[str, Any]          # original metrics (pass-through)
    summary_lines: list[str] = field(default_factory=list)  # brief bullet points


# ── Severity helpers ──────────────────────────────────────────────────────────

SEVERITY_RANK = {"OK": 0, "WARNING": 1, "CRITICAL": 2}
SEVERITY_EMOJI = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "🔴"}


def _severity(value: float, warn: float, crit: float) -> str:
    if value >= crit:
        return "CRITICAL"
    if value >= warn:
        return "WARNING"
    return "OK"


# ── Individual rules ──────────────────────────────────────────────────────────

def _rule_connections(m: dict) -> Finding:
    pct = m.get("connection_pct", 0)
    warn, crit = config.THRESHOLDS["connection_pct"]
    sev = _severity(pct, warn, crit)
    messages = {
        "OK":       f"Connection load is healthy at {pct}% ({m.get('active_connections', '?')}/{m.get('max_connections', '?')})",
        "WARNING":  f"Connection load is high at {pct}% — approaching capacity ({m.get('active_connections', '?')}/{m.get('max_connections', '?')})",
        "CRITICAL": f"Connection load is CRITICAL at {pct}% — database may start refusing connections",
    }
    return Finding(sev, "connection_pct", pct, warn, messages[sev], SEVERITY_EMOJI[sev])


def _rule_slow_queries(m: dict) -> Finding:
    sq = m.get("slow_queries", 0)
    warn, crit = config.THRESHOLDS["slow_queries"]
    sev = _severity(sq, warn, crit)
    messages = {
        "OK":       f"Slow query count is low ({sq})",
        "WARNING":  f"{sq} slow queries detected — review long-running statements",
        "CRITICAL": f"{sq} slow queries detected — this indicates a serious performance problem",
    }
    return Finding(sev, "slow_queries", sq, warn, messages[sev], SEVERITY_EMOJI[sev])


def _rule_avg_query_time(m: dict) -> Finding:
    qt = m.get("avg_query_time_ms", 0)
    warn, crit = config.THRESHOLDS["avg_query_time"]
    sev = _severity(qt, warn, crit)
    messages = {
        "OK":       f"Average query time is good ({qt}ms)",
        "WARNING":  f"Average query time is elevated at {qt}ms — investigate slow queries",
        "CRITICAL": f"Average query time is critically high at {qt}ms — immediate action needed",
    }
    return Finding(sev, "avg_query_time", qt, warn, messages[sev], SEVERITY_EMOJI[sev])


def _rule_disk_usage(m: dict) -> Finding:
    pct = m.get("disk_usage_pct", 0)
    warn, crit = config.THRESHOLDS["disk_usage"]
    sev = _severity(pct, warn, crit)
    messages = {
        "OK":       f"Disk usage is fine at {pct}% ({m.get('disk_used_mb', '?')} MB used)",
        "WARNING":  f"Disk usage is elevated at {pct}% — plan for capacity expansion",
        "CRITICAL": f"Disk usage is CRITICAL at {pct}% — risk of running out of space",
    }
    return Finding(sev, "disk_usage", pct, warn, messages[sev], SEVERITY_EMOJI[sev])


def _rule_cpu_usage(m: dict) -> Finding:
    cpu = m.get("cpu_usage_pct", 0)
    warn, crit = config.THRESHOLDS["cpu_usage"]
    sev = _severity(cpu, warn, crit)
    messages = {
        "OK":       f"CPU load is normal at {cpu}%",
        "WARNING":  f"CPU load is elevated at {cpu}% — monitor for sustained spikes",
        "CRITICAL": f"CPU load is CRITICAL at {cpu}% — database is under heavy workload",
    }
    return Finding(sev, "cpu_usage", cpu, warn, messages[sev], SEVERITY_EMOJI[sev])


def _rule_errors(m: dict) -> Finding:
    errs = m.get("error_count", 0)
    warn, crit = config.THRESHOLDS["error_count"]
    sev = _severity(errs, warn, crit)
    messages = {
        "OK":       f"Error count is low ({errs} errors)",
        "WARNING":  f"{errs} connection errors recorded — investigate aborted connections",
        "CRITICAL": f"{errs} errors detected — database connectivity is severely impacted",
    }
    return Finding(sev, "error_count", errs, warn, messages[sev], SEVERITY_EMOJI[sev])


RULES = [
    _rule_connections,
    _rule_slow_queries,
    _rule_avg_query_time,
    _rule_disk_usage,
    _rule_cpu_usage,
    _rule_errors,
]


# ── Health Score ──────────────────────────────────────────────────────────────

def _compute_health_score(findings: list[Finding]) -> int:
    """
    Weighted score: each metric contributes its weight fully if OK,
    half if WARNING, zero if CRITICAL.
    """
    metric_to_finding = {f.metric: f for f in findings}
    total_weight = sum(config.SCORE_WEIGHTS.values())
    earned = 0

    for metric, weight in config.SCORE_WEIGHTS.items():
        f = metric_to_finding.get(metric)
        if f is None:
            earned += weight  # metric not evaluated — neutral
        elif f.severity == "OK":
            earned += weight
        elif f.severity == "WARNING":
            earned += weight * 0.5
        # CRITICAL → 0

    return round((earned / total_weight) * 100)


# ── Delta Comparison ──────────────────────────────────────────────────────────

COMPARABLE_KEYS = [
    "active_connections", "connection_pct",
    "slow_queries", "avg_query_time_ms",
    "disk_usage_pct", "cpu_usage_pct", "error_count",
]


def _compute_deltas(current: dict, previous: dict | None) -> dict[str, float]:
    if not previous:
        return {}
    deltas = {}
    for key in COMPARABLE_KEYS:
        cur = current.get(key)
        prev = previous.get(key)
        if isinstance(cur, (int, float)) and isinstance(prev, (int, float)) and prev != 0:
            deltas[key] = round(((cur - prev) / prev) * 100, 1)  # % change
    return deltas


# ── Main Analyzer ─────────────────────────────────────────────────────────────

def analyze(
    metrics: dict[str, Any],
    previous_metrics: dict[str, Any] | None = None,
) -> AnalysisResult:
    """
    Evaluate metrics against all rules and produce a structured result.

    Args:
        metrics:          Output of metrics_collector.collect()
        previous_metrics: Optional previous run's metrics for delta comparison

    Returns:
        AnalysisResult with overall_status, health_score, findings, issues, deltas
    """
    logger.info("Running health analysis...")

    findings: list[Finding] = []
    for rule in RULES:
        try:
            finding = rule(metrics)
            findings.append(finding)
            logger.debug("Rule %s → %s: %s", finding.metric, finding.severity, finding.message)
        except Exception as exc:
            logger.error("Rule evaluation error: %s", exc)

    issues = [f for f in findings if f.severity in ("WARNING", "CRITICAL")]

    # Overall status = worst individual severity
    if any(f.severity == "CRITICAL" for f in findings):
        overall = "CRITICAL"
    elif any(f.severity == "WARNING" for f in findings):
        overall = "WARNING"
    else:
        overall = "OK"

    health_score = _compute_health_score(findings)
    deltas = _compute_deltas(metrics, previous_metrics)

    # Brief summary lines for Slack / AI prompt
    summary_lines = []
    for f in findings:
        trend = ""
        delta = deltas.get(f.metric)
        if delta is not None:
            arrow = "↑" if delta > 0 else "↓"
            trend = f" ({arrow}{abs(delta)}% vs last week)"
        summary_lines.append(f"{f.emoji} [{f.severity}] {f.message}{trend}")

    result = AnalysisResult(
        overall_status=overall,
        health_score=health_score,
        findings=findings,
        issues=issues,
        deltas=deltas,
        metrics=metrics,
        summary_lines=summary_lines,
    )

    logger.info(
        "Analysis complete. Status=%s, Score=%d, Issues=%d",
        overall, health_score, len(issues),
    )
    return result
