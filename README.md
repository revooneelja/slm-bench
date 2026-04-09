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
**Production considerations**
This project benchmarks three local SLMs on a single-user laptop. The results are valid for that context. Before using any of these models in production, the gaps below are worth understanding.

**What the benchmark numbers don't capture**
Concurrency degrades TTFT severely on CPU.
Every measurement in this project was taken with a single request in flight. Ollama on CPU serves one request at a time by default. Under concurrent load — even 3–5 simultaneous users — TTFT climbs from ~162 ms to 1–3 seconds as requests queue. For a production API serving multiple users, you would need either a GPU (which parallelises inference), multiple Ollama instances behind a load balancer, or an async request queue with honest latency SLAs communicated to clients.
BLEU and ROUGE-L measure word overlap, not correctness.
A score of 0.59 on summarisation means the model's output shares significant vocabulary with the reference answer — it does not mean the output is factually accurate. Small quantised models hallucinate more than their full-precision equivalents, particularly on numerical reasoning and domain-specific knowledge. Any production deployment should add an output validation layer (confidence scoring, retrieval-grounded generation, or human-in-the-loop review for high-stakes tasks).
Q4_K_M quantisation trades a small but real quality ceiling.
Compared to the full FP16 weights, Q4_K_M quantisation reduces model size by ~40% with less than 3% average quality regression on standard benchmarks. That regression is not uniformly distributed — it is larger on long-context reasoning and precise numerical tasks. For most developer tooling and summarisation workloads the tradeoff is favourable. For legal document analysis or medical summarisation, evaluate the quantised model specifically against your domain before shipping.

**Real cost accounting**
The "$0/query" framing is true at the API level but incomplete as a total cost of ownership comparison.
Cost itemLocal SLMCloud APIPer-query inference$0$0.002–$0.06 (GPT-4o class)Hardware (GPU server for production throughput)$1,000–$8,000 upfront$0DevOps: model serving, monitoring, updatesEngineer timeIncludedDowntime cost if hardware failsRealNear-zeroModel upgrade pathManual re-evaluationAutomatic (with vendor risk)
Local wins clearly at low-to-medium volume (under ~5,000 queries/day on CPU, higher with GPU) and whenever data residency requirements make cloud APIs legally or contractually unavailable. Cloud APIs win on simplicity, concurrency, and access to frontier-scale models at high volume.

**Where local SLMs are production-ready today**

Internal developer tools — coding assistants, PR summarisers, doc generators for teams of 1–20 concurrent users where occasional latency spikes are acceptable
Batch processing pipelines — offline document classification, PII extraction, or structured data generation where throughput matters more than TTFT
Edge and air-gapped deployments — factory floors, clinical devices, or offline-first mobile apps where network connectivity is unreliable or prohibited
RAG retrieval layers — lightweight answer synthesis over retrieved chunks, where the LLM role is simple enough that a 7B model matches GPT-4o quality

**Where a cloud API is still the right call**

Customer-facing products where output quality directly affects retention and a quality gap is visible to end users
High-concurrency APIs (100+ requests/minute) without dedicated GPU infrastructure
Complex multi-step reasoning — legal analysis, financial modelling, code review of large codebases — where frontier model quality is non-negotiable
Rapid prototyping where engineering time spent on model serving is not justified yet


**Production hardening checklist (if you do deploy locally)**

 Add a request queue (e.g. Redis + Celery) to manage concurrency and prevent OOM under load
 Instrument TTFT, total latency, and error rate with Prometheus or a simple structured log
 Set OLLAMA_NUM_PARALLEL and OLLAMA_MAX_LOADED_MODELS explicitly — defaults are not tuned for production
 Add a model health check endpoint to your deployment so your load balancer can detect inference failures
 Pin the model version (ollama pull mistral:7b-instruct-q4_K_M) — floating tags can change behaviour on re-pull
 Run a domain-specific eval before and after any model upgrade, not just standard benchmarks
 Document your hardware spec in your deployment runbook — a model that fits in 16 GB RAM fails silently on a machine with 8 GB
