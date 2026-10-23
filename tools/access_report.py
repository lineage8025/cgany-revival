#!/usr/bin/env python3
"""彙總網站自己記的 access log（access-YYYY-MM-DD.log）。用法：access_report.py <log 資料夾> [天數，預設 7]"""
import collections, datetime, os, sys
from pathlib import Path

PAGE_EXT = {"", ".htm", ".html", ".pl", ".php", ".cgi", ".asp", ".shtml"}

folder, days = Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 7
since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
rows = []
for f in sorted(folder.glob("access-*.log")):
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) == 8 and parts[0] >= since:
            rows.append(dict(zip(("time", "ip", "country", "email", "host", "method", "path", "status"), parts)))

def is_page(r):
    path = r["path"].split("?")[0]
    return r["status"] in ("200", "404") and os.path.splitext(path)[1].lower() in PAGE_EXT and not path.startswith("/__")

pages = [r for r in rows if is_page(r)]
print(f"期間：最近 {days} 天（{rows[0]['time'][:16] if rows else '-'} ~ {rows[-1]['time'][:16] if rows else '-'} UTC）")
print(f"請求 {len(rows)} 筆，其中頁面瀏覽 {len(pages)} 次；訪客 {len({r['email'] or r['ip'] for r in rows})} 人")
by_user = collections.defaultdict(list)
for r in pages:
    by_user[r["email"] or f"(未登入) {r['ip']}"].append(r)
print("\n訪客：")
for user, rs in sorted(by_user.items(), key=lambda kv: -len(kv[1])):
    countries = ",".join(sorted({r["country"] for r in rs if r["country"]})) or "-"
    print(f"  {len(rs):5} 頁  {user}  國家 {countries}  IP {len({r['ip'] for r in rs})} 個  {rs[0]['time'][:16]} ~ {rs[-1]['time'][:16]}")
    for (host, path), n in collections.Counter((r["host"], r["path"]) for r in rs).most_common(3):
        print(f"           {n:3}  {host}{path[:70]}")
print("\n最常被看的頁面：")
for (host, path), n in collections.Counter((r["host"], r["path"].split("&")[0]) for r in pages).most_common(10):
    print(f"  {n:5}  {host}{path[:80]}")
