# Local SLM Benchmark — Windows Setup Guide

**Hardware:** 16 GB RAM · CPU-only · Windows 10/11  
**Models:** Llama 3.2 3B · Phi-3 Mini · Mistral 7B

\---

## Step 1 — Install Ollama (5 minutes)

1. Go to **https://ollama.com/download** and download the Windows installer
2. Run the `.exe` — it installs Ollama and adds it to your PATH
3. Open **PowerShell** and verify:

```powershell
ollama --version
```

You should see something like `ollama version 0.3.x`.

\---

## Step 2 — Pull the three models

Open PowerShell and run these one at a time. Each download happens once and is cached locally.

```powershell
# \~2 GB — fastest model, good for quick tasks
ollama pull llama3.2:3b

# \~2.3 GB — best speed/quality balance for coding
ollama pull phi3:mini

# \~4.1 GB — highest quality, slowest on CPU
ollama pull mistral:7b
```

> \*\*Note:\*\* On 16 GB RAM with no GPU, all weights load into system RAM.  
> Mistral 7B uses \~5 GB RAM when loaded. Close Chrome/other apps before running it.

Verify all three are installed:

```powershell
ollama list
```

\---

## Step 3 — Start Ollama server

In one PowerShell window (keep it open the whole time):

```powershell
ollama serve
```

You'll see: `Listening on 127.0.0.1:11434`

\---

## Step 4 — Set up Python environment

Open a **second** PowerShell window:

```powershell
# Create a virtual environment
python -m venv slm-bench
slm-bench\\Scripts\\Activate.ps1

# Install dependencies
pip install requests
```

That's it — the benchmark only uses `requests` from stdlib + `requests` package.

\---

## Step 5 — Run the benchmark

```powershell
python benchmark.py
```

**What happens:**

* Ollama is checked at `localhost:11434`
* Any missing models are pulled automatically
* Each model runs 2 warm-up passes (discarded), then 5 measured passes per task
* Results are saved to `results/benchmark\_YYYYMMDD\_HHMMSS.json` and `.csv`

**Expected runtime on 16 GB / CPU-only:**

|Model|Per task (5 runs)|All 5 tasks|
|-|-|-|
|Llama 3.2 3B|\~3–4 min|\~18 min|
|Phi-3 Mini|\~2–3 min|\~14 min|
|Mistral 7B|\~7–10 min|\~45 min|

> Run Mistral last, or skip it with `MODELS = \["llama3.2:3b", "phi3:mini"]` if you're short on time.

\---

## Step 6 — Test a single model interactively

To quickly verify a model works before the full benchmark:

```powershell
ollama run llama3.2:3b
```

Type a prompt and press Enter. Type `/bye` to exit.

\---

## Understanding the outputs

**`results/benchmark\_\*.json`** — full data including sample outputs from each model  
**`results/benchmark\_\*.csv`** — spreadsheet-friendly summary for charts

Key metrics:

* **TTFT p50** — median time to first token (ms). Lower = more responsive feel.
* **t/s mean** — average tokens per second. Higher = faster generation.
* **TTFT p99** — worst-case first-token latency across runs.

\---

## Troubleshooting

**"Cannot reach Ollama"** → Make sure `ollama serve` is running in another terminal

**Mistral crashes / OOM** → Close all browser tabs, Slack, etc. You need \~6 GB free RAM. Run `taskmgr` to check available memory before starting Mistral.

**PowerShell execution policy error** → Run this first:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Slow speeds (< 5 t/s)** → Normal on CPU for Mistral 7B. Phi-3 and Llama 3.2 should be 15–30 t/s on a modern Intel/AMD CPU.

\---

## What to add next (portfolio enhancements)

* `plot\_results.py` — auto-generate bar charts from the JSON output using matplotlib
* Add BLEU/ROUGE scoring by installing `sacrebleu` and comparing against reference answers
* Add a `--task` flag to run only one task category
* Wrap in a Streamlit UI for a live interactive demo

