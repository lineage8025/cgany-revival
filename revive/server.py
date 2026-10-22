import collections, html, mimetypes, os, posixpath, re, threading, traceback, unicodedata, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ARCHIVES = [Path(p) for p in os.environ.get("CGANY_ARCHIVES", "/data/cgany_archive,/data/cgany_com_archive").split(",")]
OVERRIDE = Path(os.environ.get("CGANY_OVERRIDE", "/data/override")).resolve()
PORT = int(os.environ.get("PORT", "8000"))
CUTOFF = os.environ.get("CUTOFF", "2013")
BASE_DOMAIN = os.environ.get("BASE_DOMAIN", "").strip().strip(".").lower()
PUBLIC = bool(BASE_DOMAIN)
SUBDOMAIN_SEP = "-" if os.environ.get("SUBDOMAIN_SEP") == "-" and BASE_DOMAIN.count(".") >= 2 else "."
COOKIE_DOMAIN = BASE_DOMAIN.split(".", 1)[1] if SUBDOMAIN_SEP == "-" else BASE_DOMAIN
PUBLIC_SCHEME = os.environ.get("PUBLIC_SCHEME") or "https"
WAYBACK_EXTERNAL = os.environ.get("WAYBACK_EXTERNAL", "0") == "1"
PRIVATE_PAGES = os.environ.get("PRIVATE_PAGES", "0") == "1" and not PUBLIC
AGE_GATE = (os.environ.get("AGE_GATE") or "1") == "1"
MASK_EMAILS = (os.environ.get("MASK_EMAILS") or ("1" if PUBLIC else "0")) == "1"
ADULT = (("hcg.cgany.com", "/"), ("cgany.itaiwan.net", "/hcg/"), ("www.cgany.com", "/hcg/"), ("www.cgany.com", "/q7q7/"))
ADULT_BOARDS = ("hcg.cgany.com/", "www.cgany.com/hcg/", "www.cgany.com/q7q7/")

HOST_ALIAS = {"cgany.com": "www.cgany.com", "www.cg.cgany.com": "cg.cgany.com", "www.hcg.cgany.com": "hcg.cgany.com"}
BOARD_ALIAS = {f"cgany.itaiwan.net/{b}/": f"{b}.cgany.com/" for b in ("cg", "do", "test", "hcg")}
DIR_INDEX = ("index.html", "index.htm", "default.htm")
HTML_EXT = {"", ".htm", ".html", ".pl", ".cgi", ".php", ".asp", ".aspx", ".shtml"}
AUDIO_SHIM = ("<script>a='<audio id=\"iwater\" autoplay src=\"';b='\" data-src=\"';c='\"></audio>';"
              "var iwMode=mode;mode=function(){var e=document.getElementById('iwater');"
              "if(songPlaying&&e&&e.paused){e.play();return;}iwMode();};"
              "var iwIn=bgm_in;bgm_in=function(t){iwIn(t);clearTimeout(timer);var e=document.getElementById('iwater');"
              "if(e){e.onended=function(){bgm_in(nextTrack);};e.onerror=function(){setTimeout(function(){bgm_in(nextTrack);},3000);};}};</script>")
AUDIO_TYPES = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".ogg": "audio/ogg", ".opus": "audio/ogg",
               ".flac": "audio/flac", ".wav": "audio/wav", ".webm": "audio/webm"}
PLAYLIST_LINE = re.compile(r"""^\s*listTrack\(\s*'([^']*)'\s*,\s*"([^"]*)"\s*,\s*(\d+)\s*,\s*(\d+)\s*\)""", re.M)
LINK_NOTES = {"www.cgany.com/menuex2.htm": "原站長遺留的選單，不知道是做什麼用的（點進去只有「測試」）"}
PRIVATE_NOTE ="這一頁含當年會員的個資，預設不提供。要瀏覽請設 PRIVATE_PAGES=1 後重啟。"
EMAIL = re.compile(r"([\w.+-]+)(?:@|%40|&#64;|&#x40;)((?:[\w-]+\.)+[A-Za-z]{2,})", re.I)
IMAGE_MAGIC = {b"GIF87a": "image/gif", b"GIF89a": "image/gif", b"\xff\xd8\xff": "image/jpeg", b"\x89PNG\r\n": "image/png"}


def split_url(url):
    s = urllib.parse.urlsplit(url)
    host = (s.hostname or "").lower()
    return HOST_ALIAS.get(host, host), s.path or "/", s.query


def canon(path, query, raw_query=None):
    q = urllib.parse.unquote_to_bytes(query) if raw_query is None else raw_query
    parts = [p for p in q.replace(b"&amp;", b"&").split(b"&") if p and p != b"amp" and not p.startswith(b"sid=")]
    key = urllib.parse.unquote_to_bytes(path)
    return key + b"?" + b"&".join(parts) if parts else key


def board_of(host, path):
    board = host + "/".join(s for s in path.split("/")[:-1] if not s.endswith(".pl")) + "/"
    return BOARD_ALIAS.get(board, board)


def is_cgany(host):
    return host.endswith("cgany.com") or host == "cgany.itaiwan.net"


def public_host(host):
    if not PUBLIC:
        return f"{host}.localhost"
    label = "itaiwan" if host == "cgany.itaiwan.net" else host[: -len("cgany.com")].rstrip(".")
    return f"{label}{SUBDOMAIN_SEP}{BASE_DOMAIN}" if label else BASE_DOMAIN


def origin_host(name):
    name = name.lower()
    if not valid_host(name):
        return None
    if not PUBLIC:
        return name[: -len(".localhost")] if name.endswith(".localhost") and name.count(".") > 1 else None
    if name == BASE_DOMAIN:
        return "cgany.com"
    if name.endswith(SUBDOMAIN_SEP + BASE_DOMAIN):
        label = name[: -len(BASE_DOMAIN) - 1]
        return "cgany.itaiwan.net" if label == "itaiwan" else f"{label}.cgany.com"


def site_url(host, port):
    return f"{PUBLIC_SCHEME}://{public_host(host)}" if PUBLIC else f"http://{public_host(host)}:{port}"


def local_link(url, port, path_mode):
    host, path, query = split_url(url)
    rest = path + ("?" + query if query else "")
    return f"/_/{host}{rest}" if path_mode else site_url(host, port) + rest


def is_adult(host, path):
    path = posixpath.normpath(re.sub(r"/+", "/", urllib.parse.unquote(path).lower()) or "/")
    board = board_of(host, path + "/x")
    return any(host == h and (path + "/").startswith(p) for h, p in ADULT) or any(board.startswith(b) for b in ADULT_BOARDS)


def mask_emails(text):
    return EMAIL.sub(lambda m: m.group(1)[0] + "***@" + m.group(2), text) if MASK_EMAILS else text


def valid_host(host):
    return re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*", host or "") is not None


def article_id(query):
    q = urllib.parse.parse_qs(query)
    if q.get("act") == ["click"] and q.get("file"):
        return q["file"][0]


def is_private(host, path):
    path = urllib.parse.unquote(path).lower()
    return host == "cgany.itaiwan.net" and (path.startswith("/phpadm") or path.startswith("/vbb/member.php"))


class Archive:
    def __init__(self):
        self.exact, self.nocase, self.articles, self.scripts = {}, {}, {}, {}
        self.hosts = {}
        self.boards, self.templates, self.overview_progress = None, {}, (0, 0)
        for root in ARCHIVES:
            for idx in sorted(root.glob("index*.tsv")):
                for line in open(idx, encoding="utf-8", errors="replace"):
                    cols = line.rstrip("\n").split("\t")
                    if len(cols) >= 3 and cols[1][:4] < CUTOFF:
                        self.add(cols[0], cols[1], root / cols[2].replace("\\", "/"))

    def add(self, url, ts, file):
        host, path, query = split_url(url)
        entry = (ts, file, url, Path(path).name)
        key = (host, canon(path, query))
        if key not in self.exact or self.exact[key][0] < ts:
            self.exact[key] = entry
            self.nocase[(host, key[1].lower())] = entry
        self.hosts[host] = self.hosts.get(host, 0) + 1
        if path.endswith(".pl"):
            board = board_of(host, path)
            aid = article_id(query)
            bucket = self.articles.setdefault((board, aid), []) if aid else self.scripts.setdefault((board, canon("", query)), [])
            bucket.append(entry)

    def find(self, host, path, query):
        keys = [canon(path, query)]
        raw = urllib.parse.unquote_to_bytes(query)
        if not raw.isascii():
            try:
                keys.append(canon(path, "", raw.decode("utf-8").encode("cp950")))
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass
        if path.endswith("/") and not query:
            keys += [canon(path + name, "") for name in DIR_INDEX]
        for k in keys:
            if (host, k) in self.exact:
                return self.exact[(host, k)]
        for k in keys:
            if (host, k.lower()) in self.nocase:
                return self.nocase[(host, k.lower())]
        if path.endswith(".pl"):
            board, aid, script = board_of(host, path), article_id(query), Path(path).name
            pool = self.articles.get((board, aid)) if aid else None if query else self.scripts.get((board, b""))
            if pool:
                return max(pool, key=lambda e: (e[3] == script, e[0]))

    def build_overview(self):
        templates, views = {}, {}
        for (board, query), pool in self.scripts.items():
            if b"act=" in query:
                continue
            for ts, file, url, _ in pool:
                try:
                    text = hide_spam(decode(file.read_bytes()))
                except OSError:
                    continue
                roles, rows = parse_list(text)
                for row in rows:
                    cells, aid = CELL.findall(row), ARTICLE_ID.search(row)[1]
                    count = strip_tags(cells[roles.index("views")][1]) if "views" in roles else ""
                    if count.isdigit():
                        views[(board, aid)] = max(int(count), views.get((board, aid), 0))
                if len(rows) >= 2 and {"subject", "posted"} <= set(roles) and PAGE_SELECT.search(text):
                    score = (sum((board, i) in self.articles for i in ARTICLE_ID.findall(text)), ts)
                    for key in ((board, split_url(url)[0]), (board, None)):
                        if key not in templates or templates[key][0] < score:
                            templates[key] = (score, text, url, ts, roles, rows[:2])
        self.templates = templates
        boards = {}
        items = list(self.articles.items())
        for i, ((board, aid), pool) in enumerate(items, 1):
            self.overview_progress = (i, len(items))
            ts, file, url, _ = max(pool, key=lambda e: e[0])
            try:
                text = decode(file.read_bytes())
            except OSError:
                continue
            tag = re.search(r"(?is)<title>(.*?)</title>", text)
            subject, _, name = html.unescape(tag.group(1)).strip().rpartition("-") if tag else ("", "", "")
            plain = html.unescape(re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", text)))
            m, times = POST_INFO.search(plain), POST_TIME.findall(plain)
            item = {"aid": aid, "url": url, "views": views.get((board, aid)), "ok": bool(m and times),
                    "replies": max(len(times) - 1, 0), "last": times[-1] if len(times) > 1 else ""}
            if item["ok"]:
                item.update(key=f"{m[2]}/{int(m[3]):02}/{int(m[4]):02} {int(m[5]):02}:{m[6]}", title=m[1] or subject, author=m[7], time=times[0])
            else:
                item.update(key=aid[:4], title=subject or "（存檔內容不完整）", author="", time="")
            b = boards.setdefault(board, {"names": collections.Counter(), "items": [], "spam": 0})
            if name:
                b["names"][name] += 1
            if is_spam(item["title"], f"{item['title']} {item['author']}"):
                b["spam"] += 1
            else:
                b["items"].append(item)
        for b in boards.values():
            b["items"].sort(key=lambda it: it["key"])
            b["name"] = b["names"].most_common(1)[0][0] if b["names"] else ""
        self.boards = boards


def decode(data):
    for bom, enc in ((b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if data.startswith(bom):
            return data.decode(enc, "replace")
    m = re.search(rb"charset\s*=\s*[\"']?\s*([\w-]+)", data[:4096], re.I)
    declared = m.group(1).lower() if m else None
    encodings = ("cp950", "big5hkscs") if declared and declared not in (b"utf-8", b"utf8") else ("utf-8", "cp950", "big5hkscs")
    for enc in encodings:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("cp950", "replace")


POST_INFO = re.compile(r"主題\s*[:：]\s*(.*?)\s*(?:發表)?時間\s*[:：]\s*(\d{4})/(\d{1,2})/(\d{1,2})-(\d{1,2}):(\d{2})\S*\s*(?:發表)?作者\s*[:：]\s*(\S*)")
A_TAG = re.compile(r"(?is)<a\b([^>]*)>")
HREF = re.compile(r"""(?is)\bhref\s*=\s*(["']?)([^"'\s>]+)\1""")
OPTION_TAG = re.compile(r"(?is)<option\b([^>]*)>")
OPTION_VALUE = re.compile(r"""(?is)\bvalue\s*=\s*(["']?)([^"'\s>]+)\1""")
TR = re.compile(r"(?is)<tr\b(?:(?!<tr\b).)*?</tr>")
ARTICLE_LINK = re.compile(r"(?is)<a\b[^>]*act=click[^>]*>(.*?)</a>")
ARTICLE_ID = re.compile(r"act=click&(?:amp;)?file=(\d+)")
CELL = re.compile(r"(?is)(<t[dh]\b[^>]*>)(.*?)(</t[dh]>)")
POST_TIME = re.compile(r"(?:(?<![>＞])發表時間|(?<![>＞表])時間)\s*[:：]\s*(\d{4}/\d{1,2}/\d{1,2}-\d{1,2}:\d{2}(?::\d{2})?)")
PAGE_SELECT = re.compile(r"(?is)(<select\b[^>]*location\.href[^>]*>).*?(</select>)")
LIST_ROLES = (("編號", "num"), ("主題", "subject"), ("作者", "author"), ("人氣", "views"), ("回應", "replies"),
              ("發表時間", "posted"), ("最後回應", "last"))
SPAM_WORDS = re.compile(r"(?i)cialis|viagra|levitra|tramadol|phentermine|phentramine|adipex|meridia|ultram|xanax|valium|fastin|diet pill|payday|\bloans?\b|insurance|casino|replica|ringtone")
CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯＀-￯]")
CGANY_ABS = re.compile(r"(?i)(?<![\w:/.])(?:https?:)?//((?:[a-z0-9-]+\.)*cgany\.com|cgany\.itaiwan\.net)(?::\d+)?(?=[/\"'\s>?#);\\]|$)")
EXTERNAL_ATTR = re.compile(r"""(?i)(\b(href|src|background)\s*=\s*)(["']?)(https?://[^"'\s>]+)""")
EXTERNAL_LINK = re.compile(r"""(?i)(\b(?:href|action)\s*=\s*)(["']?)(https?://[^"'\s>]+)""")
BLACKHOLE_CSS = (
    "body{margin:0;min-height:100vh;box-sizing:border-box;padding:48px 16px;text-align:center;color:#ddd;"
    "font:15px/1.8 PMingLiU,serif;background:#000;background-image:radial-gradient(1px 1px at 12px 30px,#fff,transparent),"
    "radial-gradient(1px 1px at 90px 140px,#aac,transparent),radial-gradient(2px 2px at 160px 70px,#88f,transparent),"
    "radial-gradient(1px 1px at 60px 180px,#fff,transparent);background-size:200px 200px}"
    ".hole{width:110px;height:110px;margin:0 auto 18px;border-radius:50%;box-shadow:0 0 36px #4b36c9;"
    "background:radial-gradient(circle,#000 34%,transparent 36%),conic-gradient(#000,#3b2a8a,#000,#6a4cff,#000,#2a1a6a,#000);"
    "animation:spin 5s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}"
    "h1{color:#8ab4ff;font-size:26px;margin:0 0 8px}.url{color:#888;font:13px monospace;word-break:break-all}a{color:#6cf}")
ROOT_ATTR = re.compile(r"""(?i)(\b(?:href|src|action|background)\s*=\s*["']?)/(?!/)""")


def strip_tags(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", s))).strip()


def is_spam(subject, rest):
    subject = re.sub(r"(New|Up)!$", "", subject).strip()
    if SPAM_WORDS.search(subject + " " + rest):
        return True
    if re.fullmatch(r"[A-Za-z0-9]{8,}", subject) is None or CJK.search(subject + rest):
        return False
    return (sum(c.isupper() for c in subject) >= 3 and sum(c.islower() for c in subject) >= 2) or rest.count(subject) >= 2


def hide_spam(text):
    def row(m):
        link = ARTICLE_LINK.search(m.group(0))
        return "" if link and is_spam(strip_tags(link.group(1)), strip_tags(m.group(0))) else m.group(0)
    return TR.sub(row, text)


def parse_list(text):
    rows = TR.findall(text)
    for r in rows:
        labels = [strip_tags(c[1]) for c in CELL.findall(r)]
        if "主題" in labels and "作者" in labels:
            roles = [next((role for label, role in LIST_ROLES if c.startswith(label)), None) for c in labels]
            return roles, [r for r in rows if ARTICLE_ID.search(r) and len(CELL.findall(r)) == len(roles)]
    return [], []


def fill(inner, value):
    first = [True]

    def text_node(m):
        if not m.group(1).strip():
            return m.group(0)
        v, first[0] = value if first[0] else "", False
        return f">{v}<"
    out = re.sub(r">([^<]*)<", text_node, f">{inner}<")[1:-1]
    return value + out if first[0] else out


def render_list(board, host, script, page, srh="", keyword="", year=""):
    b = (ARCHIVE.boards or {}).get(board)
    tpl = ARCHIVE.templates.get((board, host)) or ARCHIVE.templates.get((board, None))
    if not b or not tpl:
        return None
    _, text, url, ts, roles, row_tpls = tpl
    items = [it for it in reversed(b["items"]) if it["ok"]]
    years = sorted({it["key"][:4] for it in items}, reverse=True)
    if year:
        items = [it for it in items if it["key"].startswith(year)]
    if keyword:
        fields = {"srhname": ("author",), "srhsubject": ("title",)}.get(srh, ("author", "title"))
        kw = keyword.lower()
        items = [it for it in items if any(kw in it[f].lower() for f in fields)]
    per = int((re.search(r"每頁筆數[:：]\s*(?:<[^>]*>\s*)*(\d+)", text) or [0, 30])[1]) or 30
    pages = max(1, -(-len(items) // per))
    page = min(max(page, 1), pages)
    rows = []
    for n, it in enumerate(items[(page - 1) * per: page * per]):
        row_tpl = row_tpls[n % len(row_tpls)]
        values = {"num": str(len(items) - (page - 1) * per - n), "subject": html.escape(it["title"]), "author": html.escape(it["author"]),
                  "views": "&nbsp;" if it["views"] is None else str(it["views"]), "replies": str(it["replies"]),
                  "posted": it["time"], "last": it["last"] or "&nbsp;"}
        cells = []
        for (open_, inner, close), role in zip(CELL.findall(row_tpl), roles):
            if role == "subject":
                href = f"{script}?act=click&file={it['aid']}"
                inner = re.sub(r"""(?is)(<a\b[^>]*?\bhref\s*=\s*["']?)[^"'\s>]*""", lambda m: m.group(1) + href, inner, count=1)
            cells.append(open_ + (fill(inner, values[role]) if role in values else inner) + close)
        rows.append(re.match(r"(?is)<tr\b[^>]*>", row_tpl).group(0) + "".join(cells) + "</tr>")
    if not items:
        rows.append(f"<tr><td colspan={len(roles)} align=center>沒有符合的文章</td></tr>")
    tpl_rows, first = set(parse_list(text)[1]), [True]

    def swap(m):
        if m.group(0) not in tpl_rows:
            return m.group(0)
        keep, first[0] = "\0" if first[0] else "", False
        return keep
    text = TR.sub(swap, text).replace("\0", "".join(rows))
    params = {"srh": srh, "keyword": keyword, "year": year} if keyword or year else {"srh": "", "keyword": ""}
    groups = {}
    for p in range(1, pages + 1):
        chunk = items[(p - 1) * per: p * per] or [{"key": ""}]
        newest, oldest = chunk[0]["key"][:10], chunk[-1]["key"][:10]
        span = newest if newest == oldest else f"{newest}～{oldest[5:] if oldest[:4] == newest[:4] else oldest}"
        value = html.escape(f"{script}?{urllib.parse.urlencode({**params, 'page': p})}")
        groups.setdefault(newest[:4], []).append(
            f'<option value="" selected>第{p}頁 *　{span}</option>' if p == page else f'<option value="{value}">第{p}頁　{span}</option>')
    options = "".join(f'<optgroup label="{y}年">{"".join(opts)}</optgroup>' if y else "".join(opts) for y, opts in groups.items())
    text = PAGE_SELECT.sub(lambda m: m.group(1) + options + m.group(2), text, count=1)
    form = re.search(r"""(?is)<form\b[^>]*>(?:(?!</form>).)*?name\s*=\s*["']?srh\b(?:(?!</form>).)*</form>""", text)
    if form:
        year_select = (f'<select name="year" size="1" style="background-color:D0D0D0;border:1 solid black"><option value="">全部年份</option>'
                       + "".join(f'<option value="{y}"{" selected" if y == year else ""}>{y}年</option>' for y in years) + "</select>")
        f = re.sub(r"""(?i)(<form\b[^>]*?)\bmethod\s*=\s*["']?post["']?""", r"\1method=GET", form.group(0), count=1)
        f = re.sub(r"(?i)\s+selected\b", "", f)
        f = re.sub(rf"""(?i)(<option\s+value\s*=\s*["']?{re.escape(srh or 'srhname')}["']?)""", r"\1 selected", f, count=1)
        f = re.sub(r"""(?i)(<input\b[^>]*?\bname\s*=\s*["']?keyword["']?)""", lambda m: f'{m.group(1)} value="{html.escape(keyword)}"', f, count=1)
        f = re.sub(r"""(?is)(\bname\s*=\s*["']?srh\b.*?</select>)""", lambda m: m.group(1) + year_select, f, count=1)
        text = text.replace(form.group(0), f, 1)
    text = re.sub(r"(主題總數[:：]\s*(?:<[^>]*>\s*)*)\d+", lambda m: m.group(1) + str(len(items)), text)
    text = re.sub(r"(所在分頁[:：]\s*(?:<[^>]*>\s*)*)\d+", lambda m: m.group(1) + str(page), text)
    return text, url, ts


def archived(page_url, link):
    try:
        host, path, query = split_url(urllib.parse.urljoin(page_url, html.unescape(link)))
    except ValueError:
        return True
    if is_list(path, query) and (board_of(host, path), None) in ARCHIVE.templates:
        return True
    return not is_cgany(host) or ARCHIVE.find(host, path, query) is not None


def is_list(path, query):
    return path.endswith(".pl") and "act" not in urllib.parse.parse_qs(query, keep_blank_values=True)


def song_key(name):
    return re.sub(r"[\s\\/:*?\"<>|]", "", unicodedata.normalize("NFKC", name)).lower()


def local_playlist(text, host):
    folder = OVERRIDE / host / "music"
    files = {song_key(f.stem): f for f in sorted(folder.iterdir()) if f.suffix.lower() in AUDIO_TYPES} if folder.is_dir() else {}
    if not files:
        return text
    used, lines = set(), []
    for m in PLAYLIST_LINE.finditer(text):
        key = song_key(m[2])
        if key in files:
            used.add(key)
            lines.append(f"listTrack('music/{urllib.parse.quote(files[key].name)}', \"{m[2]}\", {m[3]}, {m[4]});")
    for key, f in files.items():
        if key not in used:
            title = f.stem.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"listTrack('music/{urllib.parse.quote(f.name)}', \"{title}\", 0, 0);")
    return "\n".join(lines) + "\n"


def link_note(page_url, link):
    try:
        host, path, _ = split_url(urllib.parse.urljoin(page_url, html.unescape(link)))
    except ValueError:
        return None
    return LINK_NOTES.get(host + path)


def mark_missing(text, page_url):
    def a_tag(m):
        h = HREF.search(m.group(1))
        if h and link_note(page_url, h.group(2)):
            return f'<a title="{html.escape(link_note(page_url, h.group(2)))}" style="cursor:help"{m.group(1)}>'
        return m.group(0) if not h or archived(page_url, h.group(2)) else f'<a style="opacity:.35" title="本機沒有存檔"{m.group(1)}>'

    def option_tag(m):
        v = OPTION_VALUE.search(m.group(1))
        if not v or not re.search(r"\.(pl|php|cgi|html?)\b", v.group(2), re.I) or archived(page_url, v.group(2)):
            return m.group(0)
        return f"<option disabled{m.group(1)}>"
    return OPTION_TAG.sub(option_tag, A_TAG.sub(a_tag, text))


class Handler(BaseHTTPRequestHandler):
    timeout = 60

    def host_port(self):
        hostport = self.headers.get("Host", "")
        name, _, port = hostport.rpartition(":") if ":" in hostport else (hostport, "", "")
        return name, port or str(PORT)

    def route(self):
        name, port = self.host_port()
        raw_path, _, query = self.path.partition("?")
        host = origin_host(name)
        if host:
            return HOST_ALIAS.get(host, host), raw_path, query, lambda h: site_url(h, port)
        m = re.match(r"^/_/([^/]+)(/.*)?$", raw_path) if not PUBLIC else None
        if m and valid_host(m.group(1).lower()):
            host = m.group(1).lower()
            return HOST_ALIAS.get(host, host), m.group(2), query, lambda h: f"/_/{h}"
        return None, raw_path, query, None

    def do_GET(self):
        try:
            self.handle_get()
        except Exception:
            traceback.print_exc()
            self.blackhole(500, "伺服器處理這一頁時出錯了。")

    def handle_get(self):
        host, path, query, base = self.route()
        if host is None and path in ("/", "/board"):
            path = "/__archive" + path
        if path and path.startswith("/__archive"):
            sub = path[len("/__archive"):] or "/"
            if sub == "/":
                return self.landing()
            if sub == "/board":
                return self.board_page(query)
        if path == "/__age":
            nxt = urllib.parse.parse_qs(query).get("next", ["/"])[0]
            nxt = nxt if re.fullmatch(r"/(?![/\\])[\x21-\x7e]*", nxt) else "/"
            cookie = "age18=1; Path=/; Max-Age=2592000; SameSite=Lax" + (f"; Domain={COOKIE_DOMAIN}; Secure" if PUBLIC else "")
            return self.redirect(nxt, {"Set-Cookie": cookie})
        if host is None:
            return self.page(404, "找不到", "<p>請從<a href='/__archive/'>首頁</a>進入。</p>")
        if path is None:
            return self.redirect(f"/_/{host}/")
        if AGE_GATE and is_adult(host, path) and not self.age_ok():
            return self.age_gate(base(host), base("www.cgany.com"))
        if path == "/__blackhole":
            to = urllib.parse.parse_qs(query).get("to", [""])[0]
            return self.blackhole(200, "這是連到外站的連結。當年的網站多半已經關閉或換了主人，直接點過去可能會連到不相干的網站。", to, external=True)
        if is_private(host, path) and not PRIVATE_PAGES:
            return self.blackhole(403, PRIVATE_NOTE)
        try:
            local = (OVERRIDE / host / urllib.parse.unquote(path).lstrip("/")).resolve()
            local = local if local.is_relative_to(OVERRIDE) and local.is_file() else None
        except (ValueError, OSError):
            local = None
        if local:
            return self.serve(local.read_bytes(), path, f"http://{host}{path}", "local", base, host)
        if is_list(path, query):
            q = {k: v[0] for k, v in urllib.parse.parse_qs(query).items()}
            page, year = q.get("page", "1")[:6], q.get("year", "")
            script = Path(path).name if re.fullmatch(r"[\w.-]+\.pl", Path(path).name) else "bbs.pl"
            listing = render_list(board_of(host, path), host, script, int(page) if page.isascii() and page.isdigit() else 1,
                                  q.get("srh", "") if q.get("srh") in ("srhname", "srhsubject") else "",
                                  q.get("keyword", "").strip()[:50], year if re.fullmatch(r"\d{4}", year) else "")
            if listing:
                text, url, ts = listing
                return self.send_html(text, url, ts, base, host)
        entry = ARCHIVE.find(host, path, query)
        if entry is None:
            return self.missing(host, path, query)
        ts, file, url, _ = entry
        if is_private(*split_url(url)[:2]) and not PRIVATE_PAGES:
            return self.blackhole(403, PRIVATE_NOTE)
        if AGE_GATE and is_adult(*split_url(url)[:2]) and not self.age_ok():
            return self.age_gate(base(host), base("www.cgany.com"))
        self.serve(file.read_bytes(), path, url, ts, base, host)

    def serve(self, data, path, url, ts, base, host):
        ctype = self.content_type(path, data)
        if ctype == "text/html":
            return self.send_html(decode(data), url, ts, base, host)
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            text = local_playlist(decode(data), host) if Path(path).name == "iw_listTrack.js" else decode(data)
            data, ctype = self.localize(text, base).encode("utf-8"), ctype + "; charset=utf-8"
        self.send(200, ctype, data, {"X-Archive-Timestamp": ts, "X-Archive-Original": urllib.parse.quote(url, safe=":/?&=%")})

    def send_html(self, text, url, ts, base, host):
        text = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>|<[^>]+>", lambda m: self.localize(m.group(0), base),
                      self.rewrite_html(mark_missing(hide_spam(text), url), ts, base, host))
        text = re.sub(r"""(?is)(<script\b[^>]*\bsrc\s*=\s*["']?[^"'>]*iw_system\.js["']?[^>]*>\s*</script>)""",
                      lambda m: m.group(1) + AUDIO_SHIM, text, count=1)
        self.send(200, "text/html; charset=utf-8", text.encode("utf-8"),
                  {"X-Archive-Timestamp": ts, "X-Archive-Original": urllib.parse.quote(url, safe=":/?&=%")})

    @staticmethod
    def localize(text, base):
        return CGANY_ABS.sub(lambda m: base(HOST_ALIAS.get(m.group(1).lower(), m.group(1).lower())), text)

    def do_POST(self):
        self.blackhole(405, "這是存檔重建的網站，投票、發文、回應、登入都不會送出。")

    @staticmethod
    def content_type(path, data):
        for magic, ctype in IMAGE_MAGIC.items():
            if data.startswith(magic):
                return ctype
        ext = os.path.splitext(path)[1].lower()
        if ext in AUDIO_TYPES:
            return AUDIO_TYPES[ext]
        if ext in HTML_EXT:
            head = data[:1024].lower()
            if any(tag in head for tag in (b"<html", b"<!doctype", b"<head", b"<frameset", b"<body", b"<table", b"<meta", b"<script")):
                return "text/html"
            return "text/plain"
        return mimetypes.guess_type("x" + ext)[0] or "application/octet-stream"

    @staticmethod
    def rewrite_html(text, ts, base, host):
        text = re.sub(r"(?i)(<meta[^>]*charset\s*=\s*[\"']?)[\w-]+", r"\1utf-8", text)
        if WAYBACK_EXTERNAL:
            def external(m):
                url = m.group(4)
                if re.match(r"(?i)https?://((?:[a-z0-9-]+\.)*cgany\.com|cgany\.itaiwan\.net)(?![\w.-])", url):
                    return m.group(0)
                flag = "im_" if m.group(2).lower() != "href" else ""
                return f"{m.group(1)}{m.group(3)}https://web.archive.org/web/{ts}{flag}/{url}"
            text = EXTERNAL_ATTR.sub(external, text)
        else:
            def to_blackhole(m):
                if re.match(r"(?i)https?://((?:[a-z0-9-]+\.)*cgany\.com|cgany\.itaiwan\.net)(?![\w.-])", m.group(3)):
                    return m.group(0)
                return f"{m.group(1)}{m.group(2)}{base(host)}/__blackhole?to={urllib.parse.quote(html.unescape(m.group(3)), safe='')}"
            text = EXTERNAL_LINK.sub(to_blackhole, text)
        if base(host).startswith("/"):
            text = ROOT_ATTR.sub(lambda m: f"{m.group(1)}{base(host)}/", text)
        return text

    def missing(self, host, path, query):
        orig = f"http://{host}{path}" + (f"?{query}" if query else "")
        self.blackhole(404, "這一頁沒有留下來。", orig)

    def age_ok(self):
        return re.search(r"(?:^|;)\s*age18=1\s*(?:;|$)", self.headers.get("Cookie", "")) is not None

    def age_gate(self, prefix, www):
        enter = html.escape(f"{prefix}/__age?next={urllib.parse.quote(self.path, safe='')}")
        warning = ARCHIVE.find("www.cgany.com", "/warning.htm", "")
        if warning:
            doc = re.sub(r"(?i)(<meta[^>]*charset\s*=\s*[\"']?)[\w-]+", r"\1utf-8", decode(warning[1].read_bytes()))
            doc = re.sub(r"(?i)<head>", lambda m: f'{m.group(0)}<base href="{html.escape(www)}/">', doc, count=1)
            doc = re.sub(r"(?is)(<a\b[^>]*?\bhref\s*=\s*[\"']?)[^\"'\s>]*([^>]*>\s*已滿18)", lambda m: m.group(1) + enter + m.group(2), doc, count=1)
        else:
            doc = (f"<!doctype html><meta charset=utf-8><title>成人區</title><style>{BLACKHOLE_CSS}</style><body><div class=hole></div>"
                   f"<h1>成人區</h1><p>未滿 18 歲請離開。</p><p><a href='{enter}'>已滿18</a>　<a href='javascript:history.back()'>未滿18</a></p></body>")
        self.send(200, "text/html; charset=utf-8", doc.encode("utf-8"), {"Cache-Control": "no-store"})

    def blackhole(self, status, reason, orig="", external=False):
        links = ["<a href='javascript:history.back()'>回上一頁</a>"]
        if not re.match(r"(?i)https?://", orig):
            orig = ""
        if orig and external:
            links.append(f"<a href='{html.escape(orig)}' target='_blank' rel='noopener noreferrer'>仍要前往原網址</a>")
        body = (f"<div class=hole></div><h1>你進黑洞啦！</h1><p>{reason}</p>"
                + (f"<p class=url>{html.escape(orig)}</p>" if orig else "") + f"<p>{'　'.join(links)}</p>")
        doc = f"<!doctype html><meta charset=utf-8><title>進黑洞啦</title><style>{BLACKHOLE_CSS}</style><body>{body}</body>"
        self.send(status, "text/html; charset=utf-8", doc.encode("utf-8"))

    def landing(self):
        port = self.host_port()[1]
        rows = "".join(
            f"<tr><td>{h}</td><td>{n:,}</td><td><a href='{site_url(h, port)}/'>子網域模式</a></td>"
            + ("" if PUBLIC else f"<td><a href='/_/{h}/'>路徑模式</a></td>") + "</tr>"
            for h, n in sorted(ARCHIVE.hosts.items(), key=lambda kv: -kv[1]))
        flags = f"外連圖片走 Wayback：{'開' if WAYBACK_EXTERNAL else '關'}｜會員個資頁：{'開' if PRIVATE_PAGES else '關'}｜排除 {CUTOFF} 年以後的存檔"
        if PUBLIC:
            flags = f"<a href='{site_url('www.cgany.com', port)}/'>進入模擬CG美少女</a>"
        if ARCHIVE.boards is None:
            done, total = ARCHIVE.overview_progress
            boards = f"<p>正在讀取文章標題：{done:,} / {total:,}，請稍後重新整理。</p>"
        else:
            boards = "<table border=1 cellpadding=4><tr><th>板</th><th>位置</th><th>文章</th><th>年份</th><th>已隱藏廣告</th></tr>" + "".join(
                f"<tr><td><a href='/__archive/board?b={urllib.parse.quote(k)}'>{html.escape(b['name'] or k)}</a></td><td>{k}</td>"
                f"<td>{len(b['items']):,}</td><td>{b['items'][0]['key'][:4]}–{b['items'][-1]['key'][:4]}</td><td>{b['spam']:,}</td></tr>"
                for k, b in sorted(ARCHIVE.boards.items(), key=lambda kv: -len(kv[1]["items"])) if b["items"]) + "</table>"
        self.page(200, "cgany 存檔", f"<p>{flags}</p><h2>各板文章總覽</h2>{boards}"
                  f"<h2>依網域瀏覽</h2><table border=1 cellpadding=4><tr><th>網域</th><th>頁數</th><th colspan=2>進入</th></tr>{rows}</table>")

    def board_page(self, query):
        q = urllib.parse.parse_qs(query)
        key, path_mode = q.get("b", [""])[0], q.get("mode") == ["path"]
        if ARCHIVE.boards is None:
            done, total = ARCHIVE.overview_progress
            return self.page(503, "文章總覽建立中", f"<p>正在讀取文章標題：{done:,} / {total:,}，請稍後重新整理。</p>")
        b = ARCHIVE.boards.get(key)
        if not b or not b["items"]:
            return self.page(404, "找不到這個板", "<p><a href='/__archive/'>回首頁</a></p>")
        if AGE_GATE and any(key.startswith(h + p) for h, p in ADULT) and not self.age_ok():
            prefix = self.path.split("/__archive")[0] if "/__archive" in self.path else ""
            return self.age_gate(prefix, "/_/www.cgany.com" if prefix.startswith("/_/") else site_url("www.cgany.com", self.host_port()[1]))
        years = collections.Counter(it["key"][:4] for it in b["items"])
        year = q.get("y", [min(years)])[0]
        port, mode, bq = self.host_port()[1], "&mode=path" if path_mode else "", urllib.parse.quote(key)
        nav = "　".join(f"<b>{y}</b>（{n}）" if y == year else f"<a href='/__archive/board?b={bq}&y={y}{mode}'>{y}</a>（{n}）"
                       for y, n in sorted(years.items()))
        rows = "".join(
            f"<tr{'' if it['ok'] else ' style=color:#999'}><td>{it['key']}</td><td><a href='{html.escape(local_link(it['url'], port, path_mode))}'"
            f"{'' if it['ok'] else ' style=color:#999'}>{html.escape(it['title'])}</a></td><td>{html.escape(it['author'])}</td></tr>"
            for it in b["items"] if it["key"][:4] == year)
        switch = ("" if PUBLIC else f"｜<a href='/__archive/board?b={bq}&y={year}'>改用子網域模式開文章</a>" if path_mode
                  else f"｜<a href='/__archive/board?b={bq}&y={year}&mode=path'>子網域模式打不開？改用路徑模式</a>")
        self.page(200, html.escape(f"{b['name'] or key} 文章總覽"),
                  f"<p><a href='/__archive/'>回首頁</a>｜{key}｜共 {len(b['items']):,} 篇，已隱藏 {b['spam']:,} 篇廣告{switch}</p>"
                  f"<p>{nav}</p><table border=1 cellpadding=4><tr><th>發表時間</th><th>主題</th><th>作者</th></tr>{rows}</table>")

    def page(self, status, title, body):
        doc = f"<!doctype html><meta charset=utf-8><title>{title}</title><body style='font-family:sans-serif;margin:2em'><h1>{title}</h1>{body}</body>"
        self.send(status, "text/html; charset=utf-8", doc.encode("utf-8"))

    def redirect(self, location, headers=None):
        self.send_response(302)
        self.send_header("Location", location)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send(self, status, ctype, data, headers=None):
        if MASK_EMAILS and (ctype.startswith("text/") or "javascript" in ctype):
            data = mask_emails(data.decode("utf-8")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    ARCHIVE = Archive()
    threading.Thread(target=ARCHIVE.build_overview, daemon=True).start()
    print(f"loaded {len(ARCHIVE.exact)} urls, listening on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
