#!/usr/bin/env python3
"""從 Cloudflare 拉 cgany 的登入紀錄與流量統計。用法：cf_report.py [天數，預設 7]
token 讀環境變數 CLOUDFLARE_API_TOKEN 或 ~/.config/cloudflare/cgany.env；需要 Access: Audit Logs Read 與 Zone Analytics Read。"""
import collections, datetime, json, os, sys, urllib.error, urllib.request
from pathlib import Path

ZONE, MATCH = "loveloli.org", "cgany"
days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
token = os.environ.get("CLOUDFLARE_API_TOKEN") or dict(
    l.split("=", 1) for l in (Path.home() / ".config/cloudflare/cgany.env").read_text().split() if "=" in l)["CLOUDFLARE_API_TOKEN"]


def call(path, body=None):
    req = urllib.request.Request("https://api.cloudflare.com/client/v4" + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        return json.load(e)


zone = call(f"/zones?name={ZONE}")["result"][0]
now = datetime.datetime.now(datetime.timezone.utc)
since = (now - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

d = call(f"/accounts/{zone['account']['id']}/access/logs/access_requests?limit=1000&direction=desc&since={since}")
print(f"== Cloudflare Access 登入（最近 {days} 天）")
if not d.get("success"):
    print("  讀不到：", [e.get("message") for e in d.get("errors", [])], "（token 需要 Access: Audit Logs Read）")
else:
    logins = [x for x in d["result"] if MATCH in (x.get("app_domain") or "")]
    users = collections.defaultdict(list)
    for x in logins:
        users[x.get("user_email") or "?"].append(x)
    print(f"  {len(logins)} 次登入，{len(users)} 人，被拒 {sum(1 for x in logins if not x.get('allowed'))} 次")
    for email, xs in sorted(users.items(), key=lambda kv: -len(kv[1])):
        countries = ",".join(sorted({x.get("country") or "?" for x in xs}))
        print(f"  {len(xs):4} 次  {email}  國家 {countries}  最後 {max(x['created_at'] for x in xs)[:16]}")

q = {"query": """query($z:String!,$t:Time!){viewer{zones(filter:{zoneTag:$z}){
  hosts: httpRequestsAdaptiveGroups(limit:200,filter:{datetime_geq:$t,clientRequestHTTPHost_like:"%cgany%"}){count dimensions{clientRequestHTTPHost}}
  countries: httpRequestsAdaptiveGroups(limit:50,filter:{datetime_geq:$t,clientRequestHTTPHost_like:"%cgany%"},orderBy:[count_DESC]){count dimensions{clientCountryName}}
  daily: httpRequestsAdaptiveGroups(limit:60,filter:{datetime_geq:$t,clientRequestHTTPHost_like:"%cgany%"},orderBy:[date_ASC]){count dimensions{date}}}}}""",
     "variables": {"z": zone["id"], "t": since}}
g = call("/graphql", q)
print(f"\n== Cloudflare 流量（最近 {days} 天，含被 Access 擋下的請求）")
if g.get("errors") or not g.get("data"):
    print("  讀不到：", [e.get("message") for e in g.get("errors") or []][:2], "（token 需要 Zone Analytics Read；免費方案保留天數有限）")
else:
    z = g["data"]["viewer"]["zones"][0]
    print("  每天：", "  ".join(f"{r['dimensions']['date'][5:]}={r['count']}" for r in z["daily"]))
    print("  主機：", "  ".join(f"{r['dimensions']['clientRequestHTTPHost']}={r['count']}" for r in sorted(z["hosts"], key=lambda r: -r["count"])))
    print("  國家：", "  ".join(f"{r['dimensions']['clientCountryName']}={r['count']}" for r in z["countries"][:10]))
