"""
Local SLM Benchmark — Windows CPU build
Hardware target: 16 GB RAM, no discrete GPU
Models: llama3.2:3b, phi3:mini, mistral:7b
"""

import requests
import time
import json
import statistics
import csv
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_URL  = "http://localhost:11434"
MODELS      = ["llama3.2:3b", "phi3:mini", "mistral:7b"]
WARMUP_RUNS = 2   # discarded before measuring
BENCH_RUNS  = 5   # measured runs per prompt per model
OUTPUT_DIR  = Path("results")

# ── Real-world test prompts ───────────────────────────────────────────────────
PROMPTS = {
    "summarisation": (
        "Summarise the following news article in 3 bullet points:\n\n"
        "The Reserve Bank of India held its benchmark interest rate steady at 6.5% "
        "on Wednesday, pausing its rate-hiking cycle for the fourth consecutive meeting "
        "as inflation remained above its 4% target but showed signs of easing. "
        "Governor Shaktikanta Das said the MPC voted 5-1 to keep rates unchanged while "
        "maintaining a 'withdrawal of accommodation' stance. GDP growth for FY24 was "
        "revised up to 7.0% from 6.5%, driven by robust services exports and government "
        "capital expenditure. Das cautioned that uneven global growth and volatile food "
        "prices remain key risks. Analysts widely expect the first rate cut in Q3 2025."
    ),
    "code_generation": (
        "Write a Python function that reads a CSV file and returns the top-N rows "
        "sorted by a given column in descending order. Include type hints and a "
        "brief docstring. Keep it under 25 lines."
    ),
    "qa_factual": (
        "Answer concisely: What is the difference between RAM and VRAM, "
        "and why does VRAM matter more than RAM when running large language models locally?"
    ),
    "creative_writing": (
        "Write a 100-word product description for a noise-cancelling headphone "
        "aimed at software developers who work from home. Tone: confident, slightly playful."
    ),
    "reasoning": (
        "A train leaves Mumbai at 08:00 travelling at 90 km/h toward Pune (150 km away). "
        "Another train leaves Pune at 08:30 travelling toward Mumbai at 110 km/h. "
        "At what time do they meet, and how far from Mumbai? Show your working."
    ),
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def check_ollama():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            installed = [m["name"] for m in r.json().get("models", [])]
            print(f"✓  Ollama running. Installed models: {installed or 'none yet'}\n")
            return installed
    except requests.ConnectionError:
        print("✗  Cannot reach Ollama at localhost:11434")
        print("   → Run: ollama serve  (in a separate terminal)")
        raise SystemExit(1)


def pull_if_missing(model: str, installed: list):
    if not any(model in m for m in installed):
        print(f"  ↓ Pulling {model} (first time only)…")
        r = requests.post(f"{OLLAMA_URL}/api/pull",
                          json={"name": model}, stream=True, timeout=600)
        for line in r.iter_lines():
            if line:
                data = json.loads(line)
                if "status" in data:
                    print(f"    {data['status']}", end="\r")
        print(f"\n  ✓  {model} ready")


def generate(model: str, prompt: str) -> dict:
    """
    Call Ollama /api/generate and return timing + response text.
    Returns: {ttft_ms, total_ms, tokens_generated, tokens_per_sec, text}
    """
    t0 = time.perf_counter()
    first_token_time = None
    full_text = []
    token_count = 0

    with requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": model, "prompt": prompt, "stream": True},
        stream=True,
        timeout=300,
    ) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines():
            if not raw:
                continue
            chunk = json.loads(raw)
            if first_token_time is None:
                first_token_time = time.perf_counter()
            token = chunk.get("response", "")
            full_text.append(token)
            token_count += 1
            if chunk.get("done"):
                break

    t1 = time.perf_counter()
    ttft_ms    = round((first_token_time - t0) * 1000, 1) if first_token_time else 0
    total_ms   = round((t1 - t0) * 1000, 1)
    tps        = round(token_count / ((t1 - t0) or 1), 1)

    return {
        "ttft_ms":   ttft_ms,
        "total_ms":  total_ms,
        "tokens":    token_count,
        "tps":       tps,
        "text":      "".join(full_text).strip(),
    }


def bench_model_task(model: str, task: str, prompt: str) -> dict:
    print(f"    Warm-up ({WARMUP_RUNS} runs)…", end=" ", flush=True)
    for _ in range(WARMUP_RUNS):
        generate(model, prompt)
    print("done")

    ttfts, totals, tps_list = [], [], []
    for i in range(BENCH_RUNS):
        print(f"    Run {i+1}/{BENCH_RUNS}…", end=" ", flush=True)
        r = generate(model, prompt)
        ttfts.append(r["ttft_ms"])
        totals.append(r["total_ms"])
        tps_list.append(r["tps"])
        print(f"TTFT={r['ttft_ms']}ms  {r['tps']} t/s")
    last_output = r["text"]  # keep last response for qualitative review

    return {
        "model":         model,
        "task":          task,
        "ttft_p50_ms":   round(statistics.median(ttfts), 1),
        "ttft_p99_ms":   round(max(ttfts), 1),
        "total_p50_ms":  round(statistics.median(totals), 1),
        "tps_mean":      round(statistics.mean(tps_list), 1),
        "tps_stdev":     round(statistics.stdev(tps_list) if len(tps_list) > 1 else 0, 2),
        "sample_output": last_output[:300] + ("…" if len(last_output) > 300 else ""),
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    print("=" * 60)
    print("  Local SLM Benchmark  —  Windows 16 GB CPU")
    print("=" * 60 + "\n")

    installed = check_ollama()

    for model in MODELS:
        pull_if_missing(model, installed)

    print()
    all_results = []

    for model in MODELS:
        print(f"\n{'─'*50}")
        print(f"  Model: {model}")
        print(f"{'─'*50}")
        for task, prompt in PROMPTS.items():
            print(f"\n  Task: {task}")
            row = bench_model_task(model, task, prompt)
            all_results.append(row)
            print(f"  → P50 TTFT={row['ttft_p50_ms']}ms  "
                  f"P50 total={row['total_p50_ms']}ms  "
                  f"mean {row['tps_mean']} t/s (±{row['tps_stdev']})")

    # ── Save results ──────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = OUTPUT_DIR / f"benchmark_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n✓  Full results → {json_path}")

    csv_path = OUTPUT_DIR / f"benchmark_{ts}.csv"
    fields = ["model","task","ttft_p50_ms","ttft_p99_ms",
              "total_p50_ms","tps_mean","tps_stdev","sample_output"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_results)
    print(f"✓  CSV summary    → {csv_path}")

    # ── Console summary table ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  {'Model':<18} {'Task':<20} {'TTFT p50':>9} {'t/s':>7}")
    print("=" * 60)
    for r in all_results:
        print(f"  {r['model']:<18} {r['task']:<20} "
              f"{r['ttft_p50_ms']:>8}ms  {r['tps_mean']:>6} t/s")
    print("=" * 60)
    print("\nDone. Open results/ folder to review JSON + CSV outputs.\n")


if __name__ == "__main__":
    main()
