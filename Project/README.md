# 🔍 Log File Anomaly Explainer

> **AI-powered log analysis tool that detects errors in log files and generates structured, actionable Markdown reports — powered by Groq (llama-3.3-70b-versatile, free tier).**

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Architecture & Data Flow](#architecture--data-flow)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [Streamlit Web UI](#streamlit-web-ui)
  - [CLI (Command Line)](#cli-command-line)
- [CLI Options](#cli-options)
- [Configuration](#configuration)
- [How It Works](#how-it-works)
- [Supported Log Formats](#supported-log-formats)
- [Output Report Structure](#output-report-structure)
- [Running Tests](#running-tests)
- [Dependencies](#dependencies)
- [Troubleshooting](#troubleshooting)

---

## Overview

**Log File Anomaly Explainer** takes a raw application log file, automatically finds the first critical error or anomaly, and uses the **Groq API** (free tier — `llama-3.3-70b-versatile`) to produce a clear, structured explanation — complete with root cause analysis, a suggested fix, and prevention advice.

Two interfaces are provided:

| Interface | Description |
|---|---|
| **Streamlit Web UI** (`app.py`) | Browser-based UI with file upload, history database, and downloadable reports |
| **CLI** (`backend/main.py`) | Terminal pipeline — great for scripting and on-call workflows |

---

## Features

- **Automatic anomaly detection** — regex scanner supports `ERROR`, `CRITICAL`, `FATAL`, `Exception`, `Traceback`, `SEVERE`, `EMERGENCY`
- **Timestamp parsing** — Python logging, ISO-8601, Apache/nginx, syslog formats
- **Context extraction** — configurable lines of context around the error
- **AI-powered explanation** — five structured sections via Groq API: Summary, Root Cause, Why It Happened, Suggested Fix, Prevention
- **Graceful fallback** — if API is unavailable, a rule-based mock analysis is shown and the full report is still generated and downloadable
- **Retry logic** — automatic retry with exponential backoff on connection/timeout errors; rate-limit errors wait 30 s before retry
- **Streamlit history** — SQLite-backed analysis history with search
- **Rich terminal output** — colour-coded panels and AI summary for CLI use
- **`--no-llm` / Skip LLM mode** — parse and report without any API call

---

## Project Structure

```
Project/
├── app.py                          # Streamlit web application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── .gitignore                      # Root gitignore
├── large_sample.log                # Sample log for local testing
│
└── backend/
    ├── __init__.py
    ├── main.py                     # CLI entry point (Typer + Rich)
    ├── log_parser.py               # Log file parser & error-block extractor
    ├── llm_explainer.py            # Groq LLM client & prompt logic
    ├── report_generator.py         # Markdown report formatter & writer
    ├── .gitignore
    │
    ├── services/
    │   ├── __init__.py
    │   └── llm_client.py           # Groq API wrapper with retry logic
    │
    └── examples/
        ├── sample.log              # Example log file for testing
        └── test_log_parser.py      # Unit tests for the log parser
```

> `uploads/`, `reports/`, and `database.db` are created at runtime and excluded from version control.

---

## Architecture & Data Flow

```
Log File (.log)
      │
      ▼
┌─────────────────┐
│  log_parser.py  │  regex scan → finds first error block + context lines
└────────┬────────┘
         │  log_context (dict)
         ▼
┌──────────────────────┐
│  llm_explainer.py    │  builds prompt → calls Groq API → parses 5-section response
└──────────┬───────────┘
           │  explanation (dict)
           ▼
┌───────────────────────┐
│  report_generator.py  │  renders Markdown report → writes to disk
└───────────────────────┘
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | Tested on 3.11 |
| Groq API key | Free at [console.groq.com](https://console.groq.com) |

No local model or GPU needed — Groq runs the model in the cloud for free.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/log-file-anomaly-explainer.git
cd log-file-anomaly-explainer/Project

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your API key
cp .env.example .env
# Open .env and set: GROQ_API_KEY=gsk_your_key_here
```

---

## Usage

### Streamlit Web UI

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

**Workflow:**
1. Upload a `.log` or `.txt` file
2. Choose the Groq model (default: `llama-3.3-70b-versatile`)
3. Adjust context lines if needed
4. Click **🚀 Analyze** — the app parses, calls the API, and shows a structured explanation
5. Download the Markdown report

### CLI (Command Line)

```bash
# Full pipeline with AI explanation
python backend/main.py large_sample.log

# Parse only — no API call
python backend/main.py large_sample.log --no-llm

# Use a different model
python backend/main.py large_sample.log --model mixtral-8x7b-32768

# Save report to a custom path
python backend/main.py large_sample.log --output /tmp/report.md

# Open report in browser when done
python backend/main.py large_sample.log --auto-open
```

---

## CLI Options

| Option | Default | Description |
|---|---|---|
| `logfile` | *(required)* | Path to the log file |
| `--model` | `llama-3.3-70b-versatile` | Groq model tag |
| `--output` | `anomaly_report.md` | Output path for the Markdown report |
| `--context-lines` | `20` | Lines to capture before/after the error |
| `--no-llm` | `False` | Skip the API call; produce a parse-only report |
| `--auto-open` | `False` | Open the report in the browser after saving |

---

## Configuration

Set `GROQ_API_KEY` in your `.env` file (local) or in your Render service environment (production). No other configuration is required.

**Available Groq models (free tier):**

| Model | Context | Best for |
|---|---|---|
| `llama-3.3-70b-versatile` | 128k | Best quality (default) |
| `llama-3.1-8b-instant` | 128k | Fastest responses |
| `mixtral-8x7b-32768` | 32k | Good balance |

---

## How It Works

### 1. Log Parsing (`log_parser.py`)

Scans line-by-line for the first occurrence of `ERROR`, `CRITICAL`, `FATAL`, `Exception`, `Traceback`, `SEVERE`, or `EMERGENCY`. Captures:
- Configurable context lines before the trigger
- The full traceback (consecutive indented / continuation lines)
- Timestamp (Python logging, ISO-8601, Apache, syslog)
- Severity (`ERROR`, `CRITICAL`, or `UNKNOWN`)

### 2. LLM Explanation (`llm_explainer.py`)

Builds a two-part prompt (system + user), calls the Groq API via `llm_client.py`, and parses the response into five sections: Summary, Root Cause, Why It Happened, Suggested Fix, Prevention. Falls back to a rule-based mock if the API is unavailable.

### 3. Report Generation (`report_generator.py`)

Renders a polished Markdown document with severity badge, metadata table, raw error block, all five AI sections, and a collapsible raw LLM response.

---

## Supported Log Formats

| Format | Example |
|---|---|
| Python `logging` | `2024-01-15 10:00:35,123` |
| ISO-8601 / JSON | `2024-01-15T10:00:35.123Z` |
| Apache / nginx | `[15/Jan/2024:10:00:35 +0000]` |
| syslog | `Jan 15 10:00:35` |

---

## Output Report Structure

```markdown
# 🔍 Log Anomaly Report

| Field | Value |
|---|---|
| File | app.log |
| Severity | 🟠 ERROR |
| Timestamp | 2024-01-15 10:00:35 |
| LLM model | llama-3.3-70b-versatile |

## 🤖 AI Analysis
### 📋 Summary ...
### 🎯 Root Cause ...
### 🔎 Why It Happened ...
### 🛠️ Suggested Fix ...
### 🛡️ Prevention ...

## 🚨 Raw Error Block
...
```

---

## Running Tests

```bash
cd backend
python -m pytest examples/test_log_parser.py -v
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web UI |
| `pandas` | Analysis history table |
| `openai` | Groq API client (OpenAI-compatible) |
| `python-dotenv` | `.env` file loading |
| `typer` | CLI framework |
| `rich` | Colour terminal output |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `GROQ_API_KEY` not set | Copy `.env.example` → `.env` and add your key from [console.groq.com](https://console.groq.com) |
| 401 Authentication Failed | API key is invalid — regenerate at [console.groq.com](https://console.groq.com) |
| 429 Rate Limit | Free tier has per-minute limits — wait 30 s and retry, or reduce context lines |
| `ModuleNotFoundError: backend` | Run `streamlit run app.py` from the `Project/` directory, not from inside `backend/` |
| No anomaly detected | Log has no `ERROR`/`CRITICAL`/`Exception` lines — verify the log content |

---

## 👨‍💻 Team

Built by the **PS-02** team.

| Name | Resume |
|:---:|:---:|
| **Manikandan S** | [📄 View Resume](https://drive.google.com/file/d/1CFXQHCqRVmPZ2YCqzz5ihNIA5qzeYRSm/view?usp=drivesdk) |
| **Nithish S** | [📄 View Resume](https://drive.google.com/file/d/1M-amjnNReqQJ-C3_4zqmUuQLKIozQDU2/view?usp=drive_link) |
| **Kadhir K G** | [📄 View Resume](https://drive.google.com/file/d/1dV_-uQDYHrpxE9w7PoQqBRiLikPooEcL/view?usp=sharing) |
| **Nideeshkumar A** | [📄 View Resume](https://drive.google.com/file/d/1WppEEQpHdCzqWF_PyzJjFfU4PIuooOCH/view?usp=sharing) |

*Built with Python · Groq · Streamlit · Typer · Rich*
