"""
slack_notifier.py
─────────────────
Sends the formatted health report to a Slack channel via Incoming Webhook.

Uses Slack's Block Kit for rich formatting:
  - Header with status emoji
  - Health score + date
  - Metrics snapshot (key numbers at a glance)
  - Issues detected section
  - Full AI executive summary
  - Recommendations extracted from the report
  - Footer

Entry point:
    send(analysis_result, ai_report_text) -> bool
"""

import json
import logging
import re
from datetime import datetime

import requests

import config
from analyzer import AnalysisResult

logger = logging.getLogger(__name__)

# ── Status styling ────────────────────────────────────────────────────────────

STATUS_EMOJI = {
    "OK":       "✅",
    "WARNING":  "⚠️",
    "CRITICAL": "🚨",
}

STATUS_COLOR = {
    "OK":       "#2eb886",   # green
    "WARNING":  "#f2c744",   # yellow
    "CRITICAL": "#e01e5a",   # red
}

SCORE_EMOJI = {
    range(0,  40): "🔴",
    range(40, 70): "🟡",
    range(70, 90): "🟢",
    range(90, 101): "💚",
}


def _score_emoji(score: int) -> str:
    for r, emoji in SCORE_EMOJI.items():
        if score in r:
            return emoji
    return "⬜"


# ── Block builders ────────────────────────────────────────────────────────────

def _header_block(result: AnalysisResult, report_date: str) -> dict:
    status_emoji = STATUS_EMOJI.get(result.overall_status, "ℹ️")
    score_e = _score_emoji(result.health_score)
    return {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"🩺 DB Health Report — {report_date}",
            "emoji": True,
        },
    }


def _status_block(result: AnalysisResult) -> dict:
    status_emoji = STATUS_EMOJI.get(result.overall_status, "ℹ️")
    score_e = _score_emoji(result.health_score)
    return {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f"*Overall Status*\n{status_emoji} {result.overall_status}",
            },
            {
                "type": "mrkdwn",
                "text": f"*Health Score*\n{score_e} {result.health_score} / 100",
            },
        ],
    }


def _metrics_block(m: dict) -> dict:
    def fmt(val, unit=""):
        return f"{val}{unit}" if val not in (None, "N/A", "") else "N/A"

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                "*📊 Key Metrics*\n"
                f"• Connections: `{fmt(m.get('active_connections'))} / {fmt(m.get('max_connections'))}` "
                f"({fmt(m.get('connection_pct'), '%')})\n"
                f"• Slow Queries: `{fmt(m.get('slow_queries'))}`\n"
                f"• Avg Query Time: `{fmt(m.get('avg_query_time_ms'), 'ms')}`\n"
                f"• Disk Usage: `{fmt(m.get('disk_usage_pct'), '%')}` "
                f"({fmt(m.get('disk_used_mb'), ' MB')} used)\n"
                f"• CPU Load: `{fmt(m.get('cpu_usage_pct'), '%')}`\n"
                f"• Uptime: `{fmt(m.get('uptime_hours'), ' hrs')}`\n"
                f"• Errors: `{fmt(m.get('error_count'))}`"
            ),
        },
    }


def _issues_block(result: AnalysisResult) -> dict | None:
    if not result.issues:
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ *No issues detected this week. Database is healthy!*",
            },
        }
    lines = "\n".join(f"• {f.emoji} *[{f.severity}]* {f.message}" for f in result.issues)
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*⚠️ Issues Detected*\n{lines}",
        },
    }


def _delta_block(deltas: dict) -> dict | None:
    if not deltas:
        return None
    lines = []
    for key, pct in deltas.items():
        direction = "↑" if pct > 0 else "↓"
        color = "+" if pct < 0 else "-"  # inverting: increase is usually bad
        lines.append(f"• {key}: {direction} {abs(pct)}% vs last week")
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*📈 Week-over-Week Changes*\n" + "\n".join(lines),
        },
    }


def _ai_summary_block(ai_report: str) -> dict:
    # Truncate to stay within Slack's 3000-char block limit
    truncated = ai_report[:2900] + "…" if len(ai_report) > 2900 else ai_report
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*🤖 AI Executive Summary*\n\n{truncated}",
        },
    }


def _top_tables_block(top_tables: list) -> dict | None:
    if not top_tables:
        return None
    lines = [f"• `{t.get('db_name','')}.{t.get('table_name','')}` — {t.get('size_mb','?')} MB" for t in top_tables[:5]]
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*🗃️ Largest Tables*\n" + "\n".join(lines),
        },
    }


def _footer_block(report_date: str) -> dict:
    return {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"_AI Database Health Reporter · Generated {report_date} UTC · Powered by Claude + OpenAI_",
            }
        ],
    }


def _divider() -> dict:
    return {"type": "divider"}


# ── Message builder ───────────────────────────────────────────────────────────

def build_slack_payload(
    result: AnalysisResult,
    ai_report: str,
) -> dict:
    """Build the full Slack Block Kit payload."""
    report_date = datetime.utcnow().strftime("%Y-%m-%d")
    m = result.metrics

    blocks = [
        _header_block(result, report_date),
        _divider(),
        _status_block(result),
        _divider(),
        _metrics_block(m),
        _divider(),
        _issues_block(result),
    ]

    delta_blk = _delta_block(result.deltas)
    if delta_blk:
        blocks += [_divider(), delta_blk]

    top_tables_blk = _top_tables_block(m.get("top_tables", []))
    if top_tables_blk:
        blocks += [_divider(), top_tables_blk]

    blocks += [
        _divider(),
        _ai_summary_block(ai_report),
        _divider(),
        _footer_block(report_date),
    ]

    payload = {
        "text": (
            f"🩺 DB Health Report — {result.overall_status} "
            f"(Score: {result.health_score}/100)"
        ),
        "attachments": [
            {
                "color": STATUS_COLOR.get(result.overall_status, "#aaaaaa"),
                "blocks": blocks,
            }
        ],
    }

    if config.SLACK_CHANNEL:
        payload["channel"] = config.SLACK_CHANNEL

    return payload


# ── Main sender ───────────────────────────────────────────────────────────────

def send(result: AnalysisResult, ai_report: str) -> bool:
    """
    Send the health report to Slack.

    Returns:
        True if the message was delivered successfully, False otherwise.
    """
    if not config.SLACK_WEBHOOK_URL:
        logger.error("SLACK_WEBHOOK_URL is not configured — cannot send notification.")
        return False

    payload = build_slack_payload(result, ai_report)

    logger.info("Sending Slack notification to webhook...")
    try:
        response = requests.post(
            config.SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 200 and response.text == "ok":
            logger.info("Slack notification sent successfully.")
            return True
        else:
            logger.error(
                "Slack returned unexpected response: HTTP %s — %s",
                response.status_code,
                response.text,
            )
            return False
    except requests.RequestException as exc:
        logger.error("Failed to send Slack notification: %s", exc)
        return False
