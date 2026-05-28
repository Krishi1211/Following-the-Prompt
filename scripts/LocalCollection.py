import subprocess
import socket
import json
import time
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

TARGETS = {
    "ChatGPT": ["chat.openai.com", "api.openai.com"],
    "Gemini":  ["gemini.google.com", "generativelanguage.googleapis.com"],
    "Claude":  ["claude.ai", "api.anthropic.com"],
}

# ─── Network Probing ──────────────────────────────────────────────────────────

def resolveDns(domain):
    try:
        return socket.gethostbyname(domain)
    except Exception as e:
        return str(e)

def runTraceroute(domain):
    # -m 30: max 30 hops  -q 1: 1 probe per hop  -w 2: 2s timeout per hop
    try:
        print(f"  -> Traceroute to {domain}...")
        result = subprocess.run(
            ["traceroute", "-m", "30", "-q", "1", "-w", "2", domain],
            capture_output=True, text=True, timeout=60,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Timeout"
    except Exception as e:
        return str(e)

# ─── Collection & Persistence ─────────────────────────────────────────────────

def collectLocalData(networkName):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "timestamp": datetime.now().isoformat(),
        "network": networkName,
        "targets": {},
    }

    for service, domains in TARGETS.items():
        results["targets"][service] = {}
        for domain in domains:
            print(f"[{networkName}] Testing {service} — {domain}...")
            results["targets"][service][domain] = {
                "resolved_ip": resolveDns(domain),
                "traceroute":  runTraceroute(domain),
            }
            time.sleep(2)

    filePath = f"data/local_collection_{networkName}_{timestamp}.json"
    with open(filePath, "w") as f:
        json.dump(results, f, indent=4)
    print(f"\nCollection complete. Results saved → {filePath}")

# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("AI Routing Project: Local Data Collection\n")
    networkName = input("Enter network name (e.g., college_wifi, xfinity, tmobile): ").strip()
    if not networkName:
        networkName = "unknown_network"
    collectLocalData(networkName)
