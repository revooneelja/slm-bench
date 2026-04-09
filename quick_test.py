"""
quick_test.py — verify one model works before running the full benchmark.
Usage:  python quick_test.py
"""
import requests, time, json

MODEL = "llama3.2:3b"   # change to phi3:mini or mistral:7b to test others
PROMPT = "In one sentence, what is Ollama?"

print(f"Testing {MODEL}…\n")
t0 = time.perf_counter()
first = None
tokens = []

with requests.post(
    "http://localhost:11434/api/generate",
    json={"model": MODEL, "prompt": PROMPT, "stream": True},
    stream=True, timeout=60
) as r:
    for line in r.iter_lines():
        if not line: continue
        chunk = json.loads(line)
        if first is None:
            first = time.perf_counter()
        tokens.append(chunk.get("response", ""))
        if chunk.get("done"): break

t1 = time.perf_counter()
print("Output:", "".join(tokens).strip())
print(f"\nTTFT: {(first-t0)*1000:.0f} ms")
print(f"Total: {(t1-t0)*1000:.0f} ms  |  ~{len(tokens)/((t1-t0)):.1f} t/s")
print("\n✓  Model is working. Run benchmark.py for the full suite.")
