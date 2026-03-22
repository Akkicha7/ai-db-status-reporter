# 🩺 AI Database Health Reporter

An intelligent MySQL monitoring system that collects database performance metrics, analyzes them using rule-based logic, generates plain-English executive summaries via AI, and automatically delivers weekly reports to Slack.

---

## 📐 Architecture

```
MySQL Database
      ↓
Metrics Collector  (db_connector.py + metrics_collector.py)
      ↓
Health Analyzer    (analyzer.py)
      ↓
AI Insight Generator (ai_report_generator.py)
      ↓
Slack Notifier     (slack_notifier.py)
      ↓
Scheduler          (scheduler.py)
```

---

## 📁 Project Structure

```
ai-db-health-reporter/
├── config.py               # Central configuration & env vars
├── db_connector.py         # MySQL connection management
├── metrics_collector.py    # SQL-based metrics collection
├── analyzer.py             # Rule-based health analysis
├── ai_report_generator.py  # OpenAI executive summary
├── slack_notifier.py       # Slack Webhook delivery
├── scheduler.py            # Weekly job scheduler
├── main.py                 # Entry point / orchestrator
├── logs/                   # Auto-created log directory
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependencies
└── README.md
```

---

## ⚙️ Setup

### 1. Clone & install dependencies

```bash
git clone https://github.com/yourname/ai-db-health-reporter.git
cd ai-db-health-reporter
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 3. Run once (manual)

```bash
python main.py
```

### 4. Run as weekly scheduler

```bash
python scheduler.py
```

### 5. Run as a cron job (Linux/Mac)

```bash
# Every Monday at 8:00 AM
0 8 * * 1 /path/to/venv/bin/python /path/to/ai-db-health-reporter/main.py
```

---

## 🔑 Required Environment Variables

| Variable | Description |
|---|---|
| `DB_HOST` | MySQL host (e.g. `localhost`) |
| `DB_PORT` | MySQL port (default `3306`) |
| `DB_USER` | MySQL username |
| `DB_PASSWORD` | MySQL password |
| `DB_NAME` | Target database name |
| `OPENAI_API_KEY` | OpenAI API key |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |

---

## 📊 Metrics Collected

| Metric | SQL Source |
|---|---|
| Active connections | `SHOW STATUS LIKE 'Threads_connected'` |
| Max allowed connections | `SHOW VARIABLES LIKE 'max_connections'` |
| Slow queries | `SHOW STATUS LIKE 'Slow_queries'` |
| Avg query time (ms) | `performance_schema.events_statements_summary_global_by_event_name` |
| Database uptime (hours) | `SHOW STATUS LIKE 'Uptime'` |
| Disk usage % | `information_schema.tables` size vs `@@datadir` |
| CPU usage % | `performance_schema` or `sys.host_summary` |
| Error count | `SHOW STATUS LIKE 'Connection_errors%'` |
| Table sizes (top 5) | `information_schema.tables` |
| Index usage | `performance_schema.table_io_waits_summary_by_index_usage` |

---

## 🚨 Health Rules

| Metric | Threshold | Severity |
|---|---|---|
| Connections | > 80% of max | WARNING |
| Slow queries | > 5 | WARNING |
| Slow queries | > 20 | CRITICAL |
| Avg query time | > 1000ms | WARNING |
| Avg query time | > 3000ms | CRITICAL |
| Disk usage | > 80% | WARNING |
| Disk usage | > 90% | CRITICAL |
| CPU usage | > 75% | WARNING |
| CPU usage | > 90% | CRITICAL |

---

## 💬 Example Slack Report

```
🩺 DATABASE HEALTH WEEKLY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Week of: 2024-01-15  |  🏥 Health Score: 72/100
🔴 Overall Status: WARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 KEY METRICS
• Active Connections: 84 / 100 (84%)
• Slow Queries: 3
• Avg Query Time: 620ms
• Disk Usage: 67%
• CPU Usage: 58%
• Uptime: 168.4 hrs

⚠️ ISSUES DETECTED
• 🔴 Connection load at 84% — approaching capacity
• 🟡 3 slow queries detected this week

🤖 AI EXECUTIVE SUMMARY
Your database is operating under moderate stress this week...
[Full AI-generated summary]

💡 RECOMMENDATIONS
1. Review and optimize the top 3 slow queries
2. Consider increasing max_connections or adding a connection pool
3. Schedule an index audit for high-traffic tables
```

---

## 🧩 Optional Advanced Features

- **Health Score (0–100)**: Weighted composite score — enabled by default
- **Historical Comparison**: Saves JSON snapshots per run in `logs/history/`
- **Streamlit Dashboard**: Run `streamlit run dashboard.py`
- **Email Alerts**: Configure `SMTP_*` vars in `.env`
- **Multi-DB Support**: Add multiple `[DB_*]` blocks in config

---

## 📦 Dependencies

```
mysql-connector-python
openai
requests
schedule
python-dotenv
```

---

## 🛡️ License

MIT License. Use freely, contribute back.
