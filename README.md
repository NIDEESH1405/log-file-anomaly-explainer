
<div align="center">

```
██╗      ██████╗  ██████╗     ███████╗██╗██╗     ███████╗
██║     ██╔═══██╗██╔════╝     ██╔════╝██║██║     ██╔════╝
██║     ██║   ██║██║  ███╗    █████╗  ██║██║     █████╗  
██║     ██║   ██║██║   ██║    ██╔══╝  ██║██║     ██╔══╝  
███████╗╚██████╔╝╚██████╔╝    ██║     ██║███████╗███████╗
╚══════╝ ╚═════╝  ╚═════╝     ╚═╝     ╚═╝╚══════╝╚══════╝
    █████╗ ███╗   ██╗ ██████╗ ███╗   ███╗ █████╗ ██╗     ██╗   ██╗    
   ██╔══██╗████╗  ██║██╔═══██╗████╗ ████║██╔══██╗██║     ╚██╗ ██╔╝    
   ███████║██╔██╗ ██║██║   ██║██╔████╔██║███████║██║      ╚████╔╝     
   ██╔══██║██║╚██╗██║██║   ██║██║╚██╔╝██║██╔══██║██║       ╚██╔╝      
   ██║  ██║██║ ╚████║╚██████╔╝██║ ╚═╝ ██║██║  ██║███████╗   ██║       
   ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝      
         ███████╗██╗  ██╗██████╗ ██╗      █████╗ ██╗███╗   ██╗███████╗██████╗ 
         ██╔════╝╚██╗██╔╝██╔══██╗██║     ██╔══██╗██║████╗  ██║██╔════╝██╔══██╗
         █████╗   ╚███╔╝ ██████╔╝██║     ███████║██║██╔██╗ ██║█████╗  ██████╔╝
         ██╔══╝   ██╔██╗ ██╔═══╝ ██║     ██╔══██║██║██║╚██╗██║██╔══╝  ██╔══██╗
         ███████╗██╔╝ ██╗██║     ███████╗██║  ██║██║██║ ╚████║███████╗██║  ██║
         ╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
```

# 🔍 Log File Anomaly Explainer

> **An AI-powered log analysis engine that detects critical errors, traces root causes, and delivers structured Markdown reports — in seconds.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Groq](https://img.shields.io/badge/Groq-LLaMA%203.3%2070B-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://console.groq.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-Web%20UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![SQLite](https://img.shields.io/badge/SQLite-History%20DB-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)
[![Team](https://img.shields.io/badge/Team-PS--02-8B5CF6?style=for-the-badge)](#-meet-the-team)

</div>

---

## 🗺️ Table of Contents

- [Overview](#-overview)
- [Architecture & Data Flow](#-architecture--data-flow)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Usage](#-usage)
- [CLI Options](#-cli-options)
- [Configuration](#-configuration)
- [How It Works](#-how-it-works)
- [Supported Log Formats](#-supported-log-formats)
- [Output Report Structure](#-output-report-structure)
- [Running Tests](#-running-tests)
- [Dependencies](#-dependencies)
- [Troubleshooting](#-troubleshooting)
- [Meet the Team](#-meet-the-team)

---

## 🧠 Overview

**Log File Anomaly Explainer** is an intelligent log analysis pipeline that transforms raw, noisy application logs into clear, actionable insights. Drop in any `.log` or `.txt` file — the system finds the first critical anomaly, queries the **Groq LLM API** (free tier — `llama-3.3-70b-versatile`), and returns a five-section structured explanation covering root cause, what went wrong, and how to fix and prevent it.

Two battle-tested interfaces are available:

| Interface | File | Best For |
|---|---|---|
| 🌐 **Streamlit Web UI** | `Project/app.py` | Visual analysis, upload history, report downloads |
| ⚡ **CLI Pipeline** | `Project/backend/main.py` | Scripting, automation, on-call workflows |

---

## 🏗️ Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          👤  USER                                    │
│               (Browser Upload  ──or──  CLI Terminal)                 │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    🖥️  STREAMLIT UI  (app.py)                        │
│          File upload · Model selector · Context config               │
│          History search · Report download · SQLite viewer            │
└─────────────────────────────┬───────────────────────────────────────┘
                              │  Raw .log / .txt file
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   🔎  LOG PARSER  (log_parser.py)                    │
│   Regex scan for ERROR · CRITICAL · FATAL · Exception · Traceback    │
│   Timestamp extraction · Context window · Severity classification    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │  log_context { dict }
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  🚨  ERROR DETECTION ENGINE                          │
│          First anomaly block · Traceback extraction                  │
│          Context lines before & after · Severity badge               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │  Structured error payload
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              🤖  GROQ / OLLAMA LLM  (llm_explainer.py)              │
│   System + User prompt engineering · llama-3.3-70b-versatile        │
│   Retry logic · Exponential backoff · Rate-limit handling            │
│   Fallback: rule-based mock analysis if API unavailable              │
└─────────────────────────────┬───────────────────────────────────────┘
                              │  explanation { 5 sections }
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              📝  MARKDOWN REPORT  (report_generator.py)              │
│   Summary · Root Cause · Why It Happened · Fix · Prevention          │
│   Severity badge · Metadata table · Raw error block · LLM dump      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │  anomaly_report.md
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   🗄️  SQLITE HISTORY  (database.db)                  │
│         Persistent analysis log · Searchable · Timestamped          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Anomaly Detection** | Regex scanner for `ERROR`, `CRITICAL`, `FATAL`, `Exception`, `Traceback`, `SEVERE`, `EMERGENCY` |
| 🕐 **Timestamp Parsing** | Python logging, ISO-8601, Apache/nginx, syslog formats |
| 📋 **Context Extraction** | Configurable lines of context before and after the error trigger |
| 🤖 **AI Explanation** | Five structured sections via Groq API — Summary, Root Cause, Why, Fix, Prevention |
| 🔄 **Retry Logic** | Exponential backoff on connection/timeout; 30s wait on rate-limit errors |
| 🛡️ **Graceful Fallback** | Rule-based mock analysis when API is unavailable — full report still generated |
| 🗄️ **Analysis History** | SQLite-backed history with search in the Streamlit UI |
| 🖥️ **Rich Terminal** | Colour-coded panels and AI summary for CLI use via `rich` |
| ⏭️ **`--no-llm` Mode** | Parse and report without any API call — pure regex output |

---

## 📁 Project Structure

```
log-file-anomaly-explainer/
├── requirements.txt                # Root Python dependencies
├── render.yaml                     # Render deployment config
├── README.md                       # This file
│
└── Project/
    ├── app.py                      # 🌐 Streamlit web application
    ├── requirements.txt            # Project-level dependencies
    ├── .env.example                # Environment variable template
    ├── database.db                 # 🗄️ SQLite history database (runtime)
    │
    └── backend/
        ├── __init__.py
        ├── main.py                 # ⚡ CLI entry point (Typer + Rich)
        ├── log_parser.py           # 🔎 Log file parser & error-block extractor
        ├── llm_explainer.py        # 🤖 Groq LLM client & prompt engineering
        ├── report_generator.py     # 📝 Markdown report formatter & writer
        │
        ├── services/
        │   ├── __init__.py
        │   └── llm_client.py       # Groq API wrapper with retry logic
        │
        └── examples/
            ├── sample.log          # Example log file for testing
            └── test_log_parser.py  # Unit tests for the log parser
```

> `uploads/`, `reports/`, and `database.db` are auto-created at runtime and excluded from version control.

---

## 📋 Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.10+** | Tested on 3.11 |
| **Groq API Key** | Free at [console.groq.com](https://console.groq.com) — no GPU, no local model needed |

---

## 🚀 Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/log-file-anomaly-explainer.git
cd log-file-anomaly-explainer

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your API key
cp Project/.env.example Project/.env
# Open Project/.env and set:  GROQ_API_KEY=gsk_your_key_here
```

---

## 🖥️ Usage

### Streamlit Web UI

```bash
streamlit run Project/app.py
```

Open `http://localhost:8501` in your browser.

**Workflow:**

1. Upload a `.log` or `.txt` file
2. Choose the Groq model (default: `llama-3.3-70b-versatile`)
3. Adjust context lines if needed
4. Click **🚀 Analyze** — the app parses, calls the API, and renders a structured explanation
5. Download the Markdown report or browse history

### CLI (Command Line)

```bash
# Full pipeline — AI-powered analysis
python Project/backend/main.py Project/large_sample.log

# Parse only — no API call
python Project/backend/main.py Project/large_sample.log --no-llm

# Use a different model
python Project/backend/main.py Project/large_sample.log --model mixtral-8x7b-32768

# Save report to a custom path
python Project/backend/main.py Project/large_sample.log --output /tmp/report.md

# Open report in browser when done
python Project/backend/main.py Project/large_sample.log --auto-open
```

---

## ⚙️ CLI Options

| Option | Default | Description |
|---|---|---|
| `logfile` | *(required)* | Path to the log file |
| `--model` | `llama-3.3-70b-versatile` | Groq model tag |
| `--output` | `anomaly_report.md` | Output path for the Markdown report |
| `--context-lines` | `20` | Lines to capture before/after the error |
| `--no-llm` | `False` | Skip the API call; produce a parse-only report |
| `--auto-open` | `False` | Open the report in the browser after saving |

---

## 🔧 Configuration

Set `GROQ_API_KEY` in `Project/.env` (local) or in your Render service environment (production). No other configuration is required.

**Available Groq Models (Free Tier):**

| Model | Context | Best For |
|---|---|---|
| `llama-3.3-70b-versatile` | 128k | Best quality — default |
| `llama-3.1-8b-instant` | 128k | Fastest responses |
| `mixtral-8x7b-32768` | 32k | Good quality/speed balance |

---

## 🔬 How It Works

### 1. Log Parsing — `log_parser.py`

Scans line-by-line for the first occurrence of `ERROR`, `CRITICAL`, `FATAL`, `Exception`, `Traceback`, `SEVERE`, or `EMERGENCY`. Captures:

- Configurable context lines before the trigger
- The full traceback (consecutive indented / continuation lines)
- Timestamp parsed from Python logging, ISO-8601, Apache, or syslog format
- Severity classification (`ERROR`, `CRITICAL`, or `UNKNOWN`)

### 2. LLM Explanation — `llm_explainer.py`

Builds a two-part prompt (system + user), calls the Groq API via `llm_client.py`, and parses the response into five structured sections: **Summary**, **Root Cause**, **Why It Happened**, **Suggested Fix**, **Prevention**. Falls back to a rule-based mock if the API is unavailable.

### 3. Report Generation — `report_generator.py`

Renders a polished Markdown document with a severity badge, metadata table, raw error block, all five AI sections, and a collapsible raw LLM response section.

---

## 📂 Supported Log Formats

| Format | Example Timestamp |
|---|---|
| Python `logging` | `2024-01-15 10:00:35,123` |
| ISO-8601 / JSON | `2024-01-15T10:00:35.123Z` |
| Apache / nginx | `[15/Jan/2024:10:00:35 +0000]` |
| syslog | `Jan 15 10:00:35` |

---

## 📄 Output Report Structure

```markdown
# 🔍 Log Anomaly Report

| Field     | Value                        |
|-----------|------------------------------|
| File      | app.log                      |
| Severity  | 🟠 ERROR                     |
| Timestamp | 2024-01-15 10:00:35          |
| LLM Model | llama-3.3-70b-versatile      |

## 🤖 AI Analysis
### 📋 Summary
### 🎯 Root Cause
### 🔎 Why It Happened
### 🛠️ Suggested Fix
### 🛡️ Prevention

## 🚨 Raw Error Block
<error traceback here>

<details><summary>🔩 Raw LLM Response</summary>
...
</details>
```

---

## 🧪 Running Tests

```bash
cd Project/backend
python -m pytest examples/test_log_parser.py -v
```

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web UI framework |
| `pandas` | Analysis history table rendering |
| `openai` | Groq API client (OpenAI-compatible interface) |
| `python-dotenv` | `.env` file loading |
| `typer` | CLI framework |
| `rich` | Colour terminal output |

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| `GROQ_API_KEY` not set | Copy `.env.example` → `.env` and add your key from [console.groq.com](https://console.groq.com) |
| `401 Authentication Failed` | API key is invalid — regenerate at [console.groq.com](https://console.groq.com) |
| `429 Rate Limit` | Free tier has per-minute limits — the tool auto-waits 30s; or reduce `--context-lines` |
| `ModuleNotFoundError: backend` | Run from the project root: `streamlit run Project/app.py`, or add the project dir to `PYTHONPATH` |
| No anomaly detected | Log has no `ERROR`/`CRITICAL`/`Exception` lines — verify the log content manually |

---

## 👨‍💻 Meet the Team

<div align="center">

### Built with dedication by Team **PS-02**

*Python · Groq · Streamlit · Typer · Rich · SQLite*

---

<table>
  <tr>
    <td align="center" width="220">
      <br>
      <b>🧠 Kadhir K G</b><br>
      <sub><b>AI &amp; Project Lead</b></sub><br><br>
      <sub>Architecture design · LLM integration<br>Prompt engineering · Project direction</sub><br><br>
      <a href="https://drive.google.com/file/d/1dV_-uQDYHrpxE9w7PoQqBRiLikPooEcL/view?usp=sharing">📄 View Resume</a><br>
      <a href="mailto:kadhir@example.com">✉️ kadhir@example.com</a>
    </td>
    <td align="center" width="220">
      <br>
      <b>⚙️ Nithish S</b><br>
      <sub><b>Backend Developer</b></sub><br><br>
      <sub>Log parser · LLM explainer<br>API retry logic · CLI pipeline</sub><br><br>
      <a href="https://drive.google.com/file/d/1M-amjnNReqQJ-C3_4zqmUuQLKIozQDU2/view?usp=drive_link">📄 View Resume</a><br>
      <a href="mailto:nithish@example.com">✉️ nithish@example.com</a>
    </td>
    <td align="center" width="220">
      <br>
      <b>🎨 Nideesh Kumar A</b><br>
      <sub><b>Frontend Developer</b></sub><br><br>
      <sub>Streamlit UI · Report rendering<br>UX design · File upload flows</sub><br><br>
      <a href="https://drive.google.com/file/d/1WppEEQpHdCzqWF_PyzJjFfU4PIuooOCH/view?usp=sharing">📄 View Resume</a><br>
      <a href="mailto:nideesh@example.com">✉️ nideesh@example.com</a>
    </td>
    <td align="center" width="220">
      <br>
      <b>🗄️ Manikandan S</b><br>
      <sub><b>Database Engineer</b></sub><br><br>
      <sub>SQLite history DB · Schema design<br>Query optimization · Data persistence</sub><br><br>
      <a href="https://drive.google.com/file/d/1CFXQHCqRVmPZ2YCqzz5ihNIA5qzeYRSm/view?usp=drivesdk">📄 View Resume</a><br>
      <a href="mailto:manikandan@example.com">✉️ manikandan@example.com</a>
    </td>
  </tr>
</table>

---

### 📬 Contact the Team

> Have a question, found a bug, or want to collaborate? Reach out directly:

| Name | Role | Email |
|:---:|:---:|:---:|
| Kadhir K G | AI & Project Lead | [kadhir@example.com](mailto:kadhir@example.com) |
| Nithish S | Backend Developer | [nithish@example.com](mailto:nithish@example.com) |
| Nideesh Kumar A | Frontend Developer | [nideesh@example.com](mailto:nideesh@example.com) |
| Manikandan S | Database Engineer | [manikandan@example.com](mailto:manikandan@example.com) |

---

*© 2024 Team PS-02 · Made with ❤️ and a lot of log files*

</div>
