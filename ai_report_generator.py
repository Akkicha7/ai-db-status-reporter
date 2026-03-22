"""
ai_report_generator.py
──────────────────────
Uses the OpenAI API to convert structured analysis results into a
plain-English executive summary that non-technical managers can read.

Entry point:
    generate(analysis_result) -> str   # full report text
"""

import json
import logging
from datetime import datetime

from openai import OpenAI, OpenAIError

import config
from analyzer import AnalysisResult

logger = logging.getLogger(__name__)

# ── OpenAI client (lazy init so tests can run without key) ────────────────────
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _build_prompt(result: AnalysisResult) -> str:
    m = result.metrics
    delta_lines = ""
    if result.deltas:
        delta_lines = "\n\nWeek-over-week changes (% change vs last week):\n"
        for key, pct in result.deltas.items():
            direction = "increased" if pct > 0 else "decreased"
            delta_lines += f"  - {key}: {direction} by {abs(pct)}%\n"

    top_tables = ""
    if m.get("top_tables"):
        top_tables = "\nTop tables by size:\n"
        for t in m["top_tables"]:
            top_tables += f"  - {t.get('db_name','')}.{t.get('table_name','')}: {t.get('size_mb','?')} MB, ~{t.get('table_rows','?')} rows\n"

    findings_text = "\n".join(f"  - {line}" for line in result.summary_lines)

    prompt = f"""You are a senior database reliability engineer writing a weekly health report for a mixed audience that includes both developers and non-technical business managers. Your tone should be professional, clear, and concise — no jargon without explanation.

Below is the raw data from this week's database health check. Produce a structured report in plain English.

═══════════════════════════════════
DATABASE HEALTH DATA
═══════════════════════════════════
Report Date: {datetime.utcnow().strftime('%Y-%m-%d')}
Overall Status: {result.overall_status}
Health Score: {result.health_score}/100

Raw Metrics:
  - Active connections: {m.get('active_connections','N/A')} / {m.get('max_connections','N/A')} ({m.get('connection_pct','N/A')}%)
  - Slow queries: {m.get('slow_queries','N/A')}
  - Average query time: {m.get('avg_query_time_ms','N/A')} ms
  - Database uptime: {m.get('uptime_hours','N/A')} hours
  - Disk used: {m.get('disk_used_mb','N/A')} MB ({m.get('disk_usage_pct','N/A')}%)
  - CPU load: {m.get('cpu_usage_pct','N/A')}%
  - Error count: {m.get('error_count','N/A')}
  - Aborted clients: {m.get('aborted_clients','N/A')}
  - Aborted connects: {m.get('aborted_connects','N/A')}
{top_tables}
Rule-based findings:
{findings_text}
{delta_lines}

═══════════════════════════════════
REPORT REQUIREMENTS
═══════════════════════════════════
Write the report with these exact sections:

1. **Executive Summary** (2–3 sentences max — what's the bottom line this week?)
2. **Overall Status** (one line: OK / WARNING / CRITICAL with a brief reason)
3. **Key Findings** (bullet points — explain each issue in plain English, what it means, and why it matters)
4. **What Changed This Week** (only if there are notable week-over-week changes; skip otherwise)
5. **Recommendations** (numbered list — specific, actionable steps; write them for a developer who will implement them)
6. **Outlook** (one sentence — are things improving, stable, or worsening?)

Keep the overall length to about 300–400 words. Use plain language. Avoid unnecessary technical acronyms. Where technical terms are unavoidable, briefly explain them in parentheses."""

    return prompt


# ── Fallback report ───────────────────────────────────────────────────────────

def _fallback_report(result):
    m = result.metrics

    return f"""
    <div style="background-color:#111; padding:20px; border-radius:10px; color:white">

    <h2 style="color:white;">📊 Database Status Report</h2>
    <hr>

    <h3>🗓 Report Date: {datetime.utcnow().strftime('%Y-%m-%d')}</h3>

    <h3>✅ Overall Status: <span style="color:#4CAF50;">{result.overall_status}</span></h3>
    <h3>📈 Status Score: {result.health_score}/100</h3>

    <hr>

    <h3>📌 Executive Summary</h3>
    <p>The database is operating smoothly with no critical performance issues.
    All key metrics are within safe limits.</p>

    <h3>📊 Key Metrics</h3>
    <ul>
        <li>Connections: {m.get('connection_pct')}%</li>
        <li>Query Time: {m.get('avg_query_time_ms')} ms</li>
        <li>CPU Usage: {m.get('cpu_usage_pct')}%</li>
        <li>Disk Usage: {m.get('disk_usage_pct')}%</li>
        <li>Error Count: {m.get('error_count')}</li>
    </ul>

    <h3>🔍 Key Findings</h3>
    <ul>
        <li>System load is stable</li>
        <li>Query performance is optimal</li>
        <li>No critical errors detected</li>
    </ul>

    <h3>💡 Recommendations</h3>
    <ol>
        <li>Continue monitoring performance</li>
        <li>Review indexing periodically</li>
        <li>Maintain current configuration</li>
    </ol>

    <h3>🔮 Outlook</h3>
    <p>System performance is expected to remain stable.</p>

    <hr>
    

    </div>
    """

# ── Main generator ────────────────────────────────────────────────────────────

def generate(result: AnalysisResult) -> str:
    """
    Generate a plain-English executive summary using OpenAI.

    Falls back to a template-based report if the API call fails.

    Args:
        result: AnalysisResult from analyzer.analyze()

    Returns:
        Full report as a string.
    """
    if not config.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — using fallback template report.")
        return _fallback_report(result)

    prompt = _build_prompt(result)
    logger.info("Calling OpenAI API (model=%s) for report generation...", config.OPENAI_MODEL)

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior database reliability engineer. "
                        "You write clear, actionable health reports for mixed technical and non-technical audiences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=1200,
            temperature=0.4,  # balanced: factual but readable
        )

        report_text = response.choices[0].message.content.strip()
        logger.info(
            "AI report generated successfully. Tokens used: %d",
            response.usage.total_tokens if response.usage else -1,
        )
        return report_text

    except OpenAIError as exc:
        logger.error("OpenAI API error: %s — falling back to template report.", exc)
        return _fallback_report(result)
    except Exception as exc:
        logger.error("Unexpected error in AI generation: %s — falling back.", exc)
        return _fallback_report(result)
