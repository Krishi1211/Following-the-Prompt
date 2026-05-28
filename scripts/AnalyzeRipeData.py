import json
import os
import glob
import numpy as np

# ─── Configuration ────────────────────────────────────────────────────────────

DATA_DIR = "data"

# ─── Data Loading ─────────────────────────────────────────────────────────────

def loadLatestMapping():
    mappingFiles = glob.glob(f"{DATA_DIR}/ripe_measurement_mapping_*.json")
    if not mappingFiles:
        return None, None
    latestPath = sorted(mappingFiles)[-1]
    with open(latestPath, "r") as f:
        return latestPath, json.load(f)

def loadResultFile(measurementId):
    resultPath = f"{DATA_DIR}/ripe_results_{measurementId}.json"
    if not os.path.exists(resultPath):
        return None
    with open(resultPath, "r") as f:
        return json.load(f)

# ─── Metrics Computation ──────────────────────────────────────────────────────

def computeMetrics(data):
    reachedDest = 0
    avgRtts     = []
    hopCounts   = []

    for probeRun in data:
        hops = probeRun.get("result", [])
        if not hops:
            continue
        lastHop   = hops[-1]
        validRtts = [p.get("rtt") for p in lastHop.get("result", []) if "rtt" in p]
        if validRtts:
            reachedDest += 1
            avgRtts.append(np.mean(validRtts))
            hopCounts.append(lastHop.get("hop", 0))

    totalProbes = len(data)
    successRate = (reachedDest / totalProbes * 100) if totalProbes > 0 else 0
    meanRtt     = np.mean(avgRtts)   if avgRtts    else 0
    meanHops    = np.mean(hopCounts) if hopCounts  else 0

    return {
        "totalProbes":  totalProbes,
        "reachedDest":  reachedDest,
        "successRate":  successRate,
        "meanRtt":      meanRtt,
        "meanHops":     meanHops,
    }

# ─── Reporting ────────────────────────────────────────────────────────────────

def printDomainReport(domain, measurementId, metrics):
    print(f"  Domain: {domain} (ID: {measurementId})")
    print(f"    Probes Participated:    {metrics['totalProbes']}")
    print(f"    Successful Connections: {metrics['reachedDest']} ({metrics['successRate']:.1f}%)")
    print(f"    Average RTT to Dest:   {metrics['meanRtt']:.2f} ms")
    print(f"    Average Hop Count:     {metrics['meanHops']:.1f} hops")
    print()

def printReport(mappingPath, mapping):
    print(f"--- Analysis Report: {mappingPath} ---")

    for service, domains in mapping.items():
        print(f"\n{'=' * 40}")
        print(f"  SERVICE: {service}")
        print(f"{'=' * 40}")

        for domain, measurementId in domains.items():
            data = loadResultFile(measurementId)
            if data is None:
                print(f"  [!] Missing result file for {domain} (ID: {measurementId})\n")
                continue
            metrics = computeMetrics(data)
            printDomainReport(domain, measurementId, metrics)

# ─── Entrypoint ───────────────────────────────────────────────────────────────

def main():
    mappingPath, mapping = loadLatestMapping()
    if not mapping:
        print("[!] No measurement mapping file found in data/.")
        return
    printReport(mappingPath, mapping)


if __name__ == "__main__":
    main()
