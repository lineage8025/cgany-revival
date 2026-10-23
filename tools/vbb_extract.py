#!/usr/bin/env python3
"""把 Wayback 存的 phpMyAdmin 頁面（itaiwan /phpadm/，db=cgany）裡 vBulletin 2.2 的資料列解析成 JSON。

用法：python3 -I tools/vbb_extract.py [輸出路徑]
資料目錄取自環境變數或 repo `.env` 的 CGANY_DATA；輸入唯讀，輸出預設 $CGANY_DATA/cgany_build/vbb/vbb.json。
隱私規則見 PRIVACY 區塊。stdout 只印統計，不印任何內文。
"""
import html
import json
import os
import re
import sys
import urllib.parse as up
from collections import Counter, defaultdict

def data_dir():
    if os.environ.get("CGANY_DATA"):
        return os.environ["CGANY_DATA"]
    env = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    for line in open(env, encoding="utf-8") if os.path.exists(env) else []:
        if line.startswith("CGANY_DATA="):
            return line.split("=", 1)[1].strip()
    sys.exit("請在環境變數或 repo 的 .env 設定 CGANY_DATA")


DATA = data_dir()
ARCHIVE = os.path.join(DATA, "cgany_archive", "")
INDEXES = ("index_phpadm_a.tsv", "index_phpadm_b.tsv")
DEFAULT_OUT = os.path.join(DATA, "cgany_build", "vbb", "vbb.json")
DB = "cgany"

# ---- PRIVACY ---------------------------------------------------------------
EXCLUDED_TABLES = {
    "privatemessage", "session", "adminlog", "search", "searchindex",
    "useractivation", "passwordhistory",
    # 超出工單清單的保守排除：使用者自訂欄位、訂閱關係、頭像二進位
    "userfield", "subscribethread", "subscribeforum", "customavatar",
}
USER_KEEP = ("userid", "username", "usertitle", "joindate", "posts", "usergroupid")
DROP_SUBSTR = ("email", "password", "salt", "icq", "aim", "yahoo", "msn",
               "homepage", "birthday", "signature")
# 'ip' 若用子字串會誤殺 description/script 之類欄位，改成只比對 IP 位址型欄位名
DROP_IP_RE = re.compile(r"(^|_)ip($|_|addr)|ipaddress|ip_address", re.I)
SETTING_BLANK = ("email", "password", "license", "key")

EMAIL_RE = re.compile(r"[\w.+-]+@([\w-]+\.[\w.]+)")
IPV4_RE = re.compile(r"(?<![\d.])\d{1,3}(?:\.\d{1,3}){3}(?![\d.])")


def drop_column(name):
    n = name.lower()
    return any(s in n for s in DROP_SUBSTR) or bool(DROP_IP_RE.search(n))


def scrub_text(s):
    s = EMAIL_RE.sub(lambda m: "x***@" + m.group(1), s)
    return IPV4_RE.sub("x.x.x.x", s)


# ---- 解碼 ------------------------------------------------------------------
DECODE_STATS = Counter()


def decode_field(b):
    """資料格是原始 Big5 位元組；頁面 charset 不可信，逐欄解碼。"""
    if b.isascii():
        return b.decode("ascii")
    for enc in ("cp950", "big5hkscs", "utf-8"):
        try:
            s = b.decode(enc)
            DECODE_STATS[enc] += 1
            return s
        except UnicodeDecodeError:
            continue
    DECODE_STATS["replace"] += 1
    return b.decode("cp950", errors="replace")


# ---- 頁面解析 --------------------------------------------------------------
TR_RE = re.compile(rb'<tr bgcolor="#\w+">(.*?)</tr>', re.S)
TD_RE = re.compile(rb"<td([^>]*)>(.*?)</td>", re.S)
TH_RE = re.compile(rb"<th[^>]*>(.*?)</th>", re.S)
TAG_RE = re.compile(rb"<[^>]+>")
PK_HREF_RE = re.compile(rb'href="tbl_change\.php\?[^"]*?primary_key=([^&"]+)')
PK_PAIR_RE = re.compile(r"`(\w+)`\s*=\s*'((?:[^'\\]|\\.)*)'")
FIELD_INPUT_RE = re.compile(rb'<input type="text" name="fields\[(\w+)\]" value="([^"]*)"')
FIELD_TEXTAREA_RE = re.compile(rb'<textarea name="fields\[(\w+)\]"[^>]*>(.*?)</textarea>', re.S)
SQL_TABLE_RE = re.compile(r"^SELECT \* FROM `(\w+)`")


def cell_text(raw):
    raw = raw.strip()
    if raw.startswith(b"&nbsp;"):
        raw = raw[6:]
    if raw.endswith(b"&nbsp;"):
        raw = raw[:-6]
    return html.unescape(decode_field(raw))


def parse_pk(raw):
    s = up.unquote_plus(raw.decode("ascii", "replace"))
    return tuple((c, v.replace("\\'", "'").replace("\\\\", "\\")) for c, v in PK_PAIR_RE.findall(s))


def parse_sql_page(b):
    """回傳 (columns, [(pkpairs|None, {col: str}, numeric_cols)])。"""
    cols = [html.unescape(TAG_RE.sub(b"", t).decode("ascii", "replace")).replace("\xa0", "").strip()
            for t in TH_RE.findall(b)]
    rows = []
    if not cols:
        return cols, rows
    for tr in TR_RE.findall(b):
        tds = TD_RE.findall(tr)
        if len(tds) < len(cols):
            continue
        m = PK_HREF_RE.search(tr)
        pk = parse_pk(m.group(1)) if m else None
        data = tds[-len(cols):]
        rec, num = {}, set()
        for c, (attrs, raw) in zip(cols, data):
            rec[c] = cell_text(raw)
            if b'align="right"' in attrs:
                num.add(c)
        rows.append((pk, rec, num))
    return cols, rows


def parse_change_page(b, pk):
    rec = {}
    for name, val in FIELD_INPUT_RE.findall(b):
        rec[name.decode()] = html.unescape(decode_field(val))
    for name, val in FIELD_TEXTAREA_RE.findall(b):
        rec[name.decode()] = html.unescape(decode_field(val))
    return rec


# ---- 收集 ------------------------------------------------------------------
def fmt_ts(ts):
    return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"


def collect():
    cands = defaultdict(lambda: defaultdict(list))  # table -> pkkey -> [cand]
    numeric = defaultdict(set)
    tablepk = {}
    pages = defaultdict(list)  # table -> [ts]
    columns = {}
    stats = Counter()
    for ix in INDEXES:
        with open(ARCHIVE + ix, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3 or "?" not in parts[0]:
                    continue
                url, ts, rel = parts[0], parts[1], parts[2].replace("\\", "/")
                path = url.split("?", 1)[0]
                is_sql = path.endswith("/sql.php")
                is_change = path.endswith("/tbl_change.php")
                if not (is_sql or is_change):
                    continue
                q = up.parse_qs(url.split("?", 1)[1], keep_blank_values=True)
                if q.get("db") != [DB] or "table" not in q:
                    continue
                table = q["table"][0]
                if table in EXCLUDED_TABLES:
                    continue
                try:
                    with open(ARCHIVE + rel, "rb") as fh:
                        b = fh.read()
                except OSError:
                    stats["missing_file"] += 1
                    continue
                if is_sql:
                    sq = q.get("sql_query", [""])[0]
                    m = SQL_TABLE_RE.match(sq)
                    if not m or m.group(1) != table or "primary_key" in q:
                        continue
                    cols, rows = parse_sql_page(b)
                    if cols[:2] == ["Table", "Action"]:
                        stats["sql_page_zero_rows_table_list"] += 1
                        continue
                    if not rows:
                        stats["sql_page_no_rows"] += 1
                        continue
                    pages[table].append(ts)
                    columns.setdefault(table, cols)
                    for pk, rec, num in rows:
                        numeric[table] |= num
                        if pk:
                            tablepk.setdefault(table, tuple(c for c, _ in pk))
                        cands[table][("sql", pk, tuple(rec.items()) if not pk else None)].append(
                            {"ts": ts, "src": "sql", "rec": rec, "pk": pk})
                else:
                    if "primary_key" not in q:
                        continue
                    pk = parse_pk(q["primary_key"][0].encode())
                    rec = parse_change_page(b, pk)
                    if not rec or not pk:
                        stats["change_page_empty"] += 1
                        continue
                    pages[table].append(ts)
                    tablepk.setdefault(table, tuple(c for c, _ in pk))
                    cands[table][("chg", pk, None)].append(
                        {"ts": ts, "src": "change", "rec": rec, "pk": pk})
    return cands, numeric, tablepk, pages, columns, stats


def pk_key(table, tablepk, cand):
    pk = cand["pk"]
    if pk:
        return tuple(v for _, v in pk)
    cols = tablepk.get(table)
    if cols and all(c in cand["rec"] for c in cols):
        return tuple(cand["rec"][c] for c in cols)
    return ("row",) + tuple(sorted(cand["rec"].items()))


def is_truncated_value(v):
    return v.endswith("...") and len(v) > 3


def build(cands, numeric, tablepk, pages, columns):
    out, meta = {}, {}
    conflicts = Counter()
    for table, groups in cands.items():
        by_pk = defaultdict(list)
        for lst in groups.values():
            for c in lst:
                by_pk[pk_key(table, tablepk, c)].append(c)
        recs, ntrunc, nconf, nfull = [], 0, 0, 0
        for key, lst in by_pk.items():
            # 以 tbl_change（完整值）為基準判斷 sql.php 版本是否被截斷
            full = [c for c in lst if c["src"] == "change"]
            for c in lst:
                tr = []
                for col, v in c["rec"].items():
                    if c["src"] == "sql" and is_truncated_value(v):
                        ref = [f["rec"].get(col) for f in full if f["rec"].get(col) is not None]
                        if any(r != v and r.startswith(v[:-3]) for r in ref):
                            tr.append(col)
                c["trunc"] = tr
            cols = columns.get(table, [])
            lst.sort(key=lambda c: (len(c["trunc"]), sum(1 for k in cols if k not in c["rec"]),
                                    -int(c["ts"]), c["src"] != "change"))
            best = lst[0]
            distinct = {tuple(sorted(c["rec"].items())) for c in lst if not c["trunc"]}
            if len(distinct) > 1:
                nconf += 1
            rec = {k: best["rec"][k] for k in cols if k in best["rec"]}
            rec.update({k: v for k, v in best["rec"].items() if k not in rec})
            for col in numeric[table]:
                if col in rec and re.fullmatch(r"-?\d+", rec[col]):
                    rec[col] = int(rec[col])
            if best["src"] == "change":
                nfull += 1
            rec["_snapshot"] = fmt_ts(best["ts"])
            rec["_truncated"] = bool(best["trunc"])
            if best["trunc"]:
                ntrunc += 1
            recs.append(rec)
        out[table] = recs
        ts = sorted(pages[table])
        meta[table] = {
            "rows": len(recs),
            "pages_used": len(ts),
            "truncated_rows": ntrunc,
            "full_rows_from_edit_page": nfull,
            "snapshot_conflicts": nconf,
            "snapshot_range": [fmt_ts(ts[0]), fmt_ts(ts[-1])] if ts else None,
        }
    return out, meta


def apply_privacy(out, meta):
    for table, recs in list(out.items()):
        keep_user = table == "user"
        new = []
        for rec in recs:
            r = {}
            for k, v in rec.items():
                if k.startswith("_"):
                    r[k] = v
                    continue
                if keep_user and k not in USER_KEEP:
                    continue
                if drop_column(k):
                    continue
                r[k] = scrub_text(v) if isinstance(v, str) else v
            if table == "setting":
                vn = str(rec.get("varname", "")).lower()
                if any(s in vn for s in SETTING_BLANK):
                    for k in ("value", "default"):
                        if k in r:
                            r[k] = ""
            new.append(r)
        # 依主鍵（第一個欄位）排序
        first = next((k for k in (new[0] if new else {}) if not k.startswith("_")), None)
        if first:
            new.sort(key=lambda r: (0, r[first], "") if isinstance(r.get(first), int) else (1, 0, str(r.get(first))))
        out[table] = new
        cols = [k for k in (new[0] if new else {}) if not k.startswith("_")]
        meta[table]["columns"] = cols


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    cands, numeric, tablepk, pages, columns, stats = collect()
    out, meta = build(cands, numeric, tablepk, pages, columns)
    apply_privacy(out, meta)
    result = dict(sorted(out.items()))
    result["meta"] = {
        "tables": dict(sorted(meta.items())),
        "excluded_tables": sorted(EXCLUDED_TABLES),
        "decode_stats": dict(DECODE_STATS),
        "skipped": dict(stats),
        "source": "Wayback phpMyAdmin pages, cgany.itaiwan.net/phpadm/ db=cgany",
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"wrote {out_path}")
    for t, m in sorted(meta.items()):
        print(f"{t:20s} rows={m['rows']:5d} pages={m['pages_used']:4d} trunc={m['truncated_rows']}")


if __name__ == "__main__":
    main()
