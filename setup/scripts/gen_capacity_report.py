#!/usr/bin/env python3
"""gen_capacity_report.py — ISP interface capacity report with trend forecasting.

Queries Prometheus for interface utilization, fits a linear trend, forecasts
when each interface will breach 80% capacity, and writes an HTML report.

Usage:
  python gen_capacity_report.py --prometheus http://prometheus:9090 --out report.html
  python gen_capacity_report.py --days 30 --threshold 80 --out report.html
"""
from __future__ import annotations
import argparse, json, os, sys, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path


PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")


def prom_query_range(url: str, query: str, start: float, end: float, step: str = "1h") -> list[dict]:
    params = urllib.parse.urlencode({"query": query, "start": start, "end": end, "step": step})
    req_url = f"{url}/api/v1/query_range?{params}"
    with urllib.request.urlopen(req_url, timeout=30) as r:
        data = json.loads(r.read())
    return data.get("data", {}).get("result", [])


def prom_query(url: str, query: str) -> list[dict]:
    params = urllib.parse.urlencode({"query": query})
    with urllib.request.urlopen(f"{url}/api/v1/query?{params}", timeout=30) as r:
        data = json.loads(r.read())
    return data.get("data", {}).get("result", [])


def linear_trend(xs: list[float], ys: list[float]):
    """Return (slope, intercept) via least squares."""
    n = len(xs)
    if n < 2:
        return 0.0, ys[-1] if ys else 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    slope = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / denom if denom else 0
    return slope, my - slope * mx


def days_to_breach(slope: float, intercept: float, current_x: float, threshold: float) -> float | None:
    if slope <= 0:
        return None
    days = (threshold - (intercept + slope * current_x)) / (slope * 86400)
    return days if days > 0 else None


def collect_utilization(prom_url: str, days: int) -> list[dict]:
    now = datetime.now(timezone.utc).timestamp()
    start = now - days * 86400
    query = 'rate(ifHCInOctets[1h]) * 8 / ifHighSpeed / 1000000 * 100'
    results = []
    try:
        series = prom_query_range(prom_url, query, start, now, step="1h")
    except Exception as e:
        print(f"ERROR querying Prometheus: {e}", file=sys.stderr)
        return []

    for s in series:
        labels = s["labels"]
        values = [(float(v[0]), float(v[1])) for v in s["values"] if v[1] != "NaN"]
        if not values:
            continue
        xs = [v[0] for v in values]
        ys = [v[1] for v in values]
        current = ys[-1]
        peak = max(ys)
        avg = sum(ys) / len(ys)
        slope, intercept = linear_trend(xs, ys)
        dtb = days_to_breach(slope, intercept, xs[-1], 80.0)
        results.append({
            "instance": labels.get("instance", "?"),
            "interface": labels.get("ifDescr", "?"),
            "current_pct": round(current, 1),
            "avg_pct": round(avg, 1),
            "peak_pct": round(peak, 1),
            "slope_per_day": round(slope * 86400, 3),
            "days_to_80pct": round(dtb, 0) if dtb else None,
        })

    return sorted(results, key=lambda x: x.get("days_to_80pct") or 9999)


def render_html(results: list[dict], days: int, threshold: float, prom_url: str) -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = ""
    for r in results:
        dtb = r["days_to_80pct"]
        urgency = ""
        if dtb is not None:
            if dtb < 30: urgency = ' style="background:#ffeaea"'
            elif dtb < 90: urgency = ' style="background:#fff8e1"'
        dtb_str = f"{int(dtb)}d" if dtb else "—"
        rows += f"""<tr{urgency}>
          <td>{r['instance']}</td><td>{r['interface']}</td>
          <td>{r['current_pct']}%</td><td>{r['avg_pct']}%</td>
          <td>{r['peak_pct']}%</td><td>{r['slope_per_day']:+.2f}%/day</td>
          <td><b>{dtb_str}</b></td></tr>\n"""

    critical = [r for r in results if r["days_to_80pct"] and r["days_to_80pct"] < 30]
    warning  = [r for r in results if r["days_to_80pct"] and 30 <= r["days_to_80pct"] < 90]

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>ISP Capacity Report</title>
<style>body{{font-family:sans-serif;margin:2em;color:#222}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:8px 12px;text-align:left}}
th{{background:#2c3e50;color:#fff}}tr:hover{{background:#f5f5f5}}
.badge{{display:inline-block;padding:3px 8px;border-radius:4px;font-size:12px}}
.crit{{background:#e74c3c;color:#fff}}.warn{{background:#f39c12;color:#fff}}
</style></head><body>
<h1>ISP Capacity Report</h1>
<p>Generated: {now_str} &nbsp;|&nbsp; Lookback: {days} days &nbsp;|&nbsp;
Threshold: {threshold}% &nbsp;|&nbsp; Source: {prom_url}</p>
<p>
  <span class="badge crit">{len(critical)} critical (&lt;30d)</span> &nbsp;
  <span class="badge warn">{len(warning)} warning (&lt;90d)</span> &nbsp;
  {len(results)} interfaces analysed
</p>
<table><thead><tr>
  <th>Device</th><th>Interface</th><th>Current</th><th>Avg ({days}d)</th>
  <th>Peak</th><th>Trend</th><th>Days to {threshold}%</th>
</tr></thead><tbody>{rows}</tbody></table>
</body></html>"""


def main() -> None:
    p = argparse.ArgumentParser(description="ISP interface capacity report")
    p.add_argument("--prometheus", default=PROMETHEUS_URL)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--threshold", type=float, default=80.0)
    p.add_argument("--out", default="capacity_report.html")
    args = p.parse_args()

    print(f"Querying {args.prometheus} for {args.days} days of utilization data...")
    results = collect_utilization(args.prometheus, args.days)
    if not results:
        print("No utilization data found. Check Prometheus URL and SNMP scrape jobs.")
        sys.exit(1)

    html = render_html(results, args.days, args.threshold, args.prometheus)
    Path(args.out).write_text(html)
    print(f"Report written: {args.out}  ({len(results)} interfaces)")
    critical = [r for r in results if r["days_to_80pct"] and r["days_to_80pct"] < 30]
    if critical:
        print(f"  {len(critical)} interface(s) will breach {args.threshold}% within 30 days!")

if __name__ == "__main__": main()
