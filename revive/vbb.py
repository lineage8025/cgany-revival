import datetime, html, json, math, os, re, urllib.parse
from pathlib import Path

DATA = Path(os.environ.get("VBB_DATA", "/data/vbb/vbb.json"))
HOST = "cgany.itaiwan.net"
STYLE = {"{pagebgcolor}": "#000000", "{tablebordercolor}": "#000000", "{timecolor}": "#A0A0A0", "{firstaltcolor}": "#444444",
         "{secondaltcolor}": "#333333", "<smallfont": '<font face="新細明體"', "<normalfont": '<font face="新細明體"',
         "<largefont": '<font face="新細明體" size="3"'}
THREAD_SHELL = "/vbb/showthread.php?s=&threadid=7403"
FORUM_SHELL = "/vbb/forumdisplay.php?s=&forumid=6"
ADULT_FORUMS = {16}
ORPHAN_FORUM = {"forumid": 0, "title": "其他存到的文章", "parentid": -1, "cancontainthreads": 1}
TR_OPEN = re.compile(r"(?i)<tr\b")
TABLE_TAG = re.compile(r"(?i)<(/?)table\b")
POST_TABLE = '<table bgcolor="#000000" width="100%" cellpadding="0" cellspacing="0" border="0">'


def php_date(fmt, ts):
    d = datetime.datetime.fromtimestamp(int(ts), datetime.timezone(datetime.timedelta(hours=8)))
    table = {"m": f"{d.month:02}", "d": f"{d.day:02}", "Y": str(d.year), "y": f"{d.year % 100:02}", "h": f"{(d.hour % 12) or 12:02}",
             "H": f"{d.hour:02}", "i": f"{d.minute:02}", "A": "AM" if d.hour < 12 else "PM", "M": d.strftime("%b"),
             "j": str(d.day), "n": str(d.month)}
    return "".join(table.get(c, c) for c in fmt)


def parse_vb_time(text):
    m = re.search(r"(\d\d)-(\d\d)-(\d{4})\s+(\d\d):(\d\d)\s*([AP]M)", text)
    if not m:
        return None
    hour = int(m[4]) % 12 + (12 if m[6] == "PM" else 0)
    d = datetime.datetime(int(m[3]), int(m[1]), int(m[2]), hour, int(m[5]), tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
    return int(d.timestamp())


def rpg(user, now):
    posts = int(user.get("posts") or 0)
    days = max((now - int(user.get("joindate") or now)) / 86400, 1)
    ppd = posts / days
    level = math.log10(posts) ** 3 if posts > 1 else 0
    maxhp = level * 25 * min(max(round(ppd / 6, 1), 1), 1.5)
    hp = maxhp if ppd / 10 >= 1 else math.floor(ppd / 10 * maxhp)
    maxmp = days * level / 5
    mp = min(posts / 3, maxmp)
    maxhp, maxmp = math.floor(maxhp), math.floor(maxmp)
    return {"showlevel": math.floor(level + 1), "ep": math.floor(100 * (level - math.floor(level))),
            "hp": math.floor(hp), "maxhp": maxhp, "hpf": max(math.floor(100 * hp / (maxhp or 1)) - 1, 0),
            "mp": math.floor(mp), "maxmp": maxmp, "mpf": max(math.floor(100 * mp / (maxmp or 1)) - 1, 0)}


def safe_url(url):
    url = html.unescape(url).strip()
    return html.escape(url, quote=True) if re.match(r"(?i)(https?|ftp)://", url) else None


def bbcode(text, smilies):
    t = html.escape(text.replace("\r\n", "\n"), quote=False)
    for tag in ("b", "i", "u"):
        t = re.sub(rf"(?is)\[{tag}\](.*?)\[/{tag}\]", rf"<{tag}>\1</{tag}>", t)

    def link(m):
        href = safe_url(m.group(1) or m.group(2))
        return f'<a href="{href}" target="_blank">{m.group(2)}</a>' if href else m.group(0)

    def image(m):
        src = safe_url(m.group(1))
        return f'<img src="{src}" border="0" alt="">' if src else m.group(0)
    t = re.sub(r"(?is)\[url(?:=([^\]]+))?\](.*?)\[/url\]", link, t)
    t = re.sub(r"(?is)\[img\](.*?)\[/img\]", image, t)
    t = re.sub(r"(?is)\[color=([#\w]+)\](.*?)\[/color\]", r'<font color="\1">\2</font>', t)
    t = re.sub(r"(?is)\[size=(\d)\](.*?)\[/size\]", r'<font size="\1">\2</font>', t)
    t = re.sub(r"(?is)\[font=([^\]\"<>]+)\](.*?)\[/font\]", r'<font face="\1">\2</font>', t)
    t = re.sub(r"(?is)\[email(?:=[^\]]*)?\](.*?)\[/email\]", r"\1", t)
    for _ in range(3):
        t = re.sub(r"(?is)\[quote\](.*?)\[/quote\]",
                   r'<blockquote><font face="新細明體">引言:</font><hr>\1<hr></blockquote>', t)
    t = re.sub(r"(?is)\[code\](.*?)\[/code\]", r'<blockquote><font face="新細明體">程式碼:</font><hr><pre>\1</pre><hr></blockquote>', t)
    t = re.sub(r"(?is)\[list\](.*?)\[/list\]", lambda m: "<ul>" + re.sub(r"\[\*\]", "<li>", m.group(1)) + "</ul>", t)
    for text_, path in smilies:
        t = t.replace(html.escape(text_, quote=False), f'<img src="{path}" border="0" alt="{html.escape(text_)}" align="absmiddle">')
    return t.replace("\n", "<br />\n")


def balanced_end(text, start, tag_re):
    depth = 0
    for m in tag_re.finditer(text, start):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return text.find(">", m.end()) + 1
    return len(text)


def outer_rows(text, marker):
    rows, pos = [], 0
    for m in re.finditer(r'(?i)<tr align="center">', text):
        if m.start() < pos:
            continue
        end = balanced_end(text, m.start(), re.compile(r"(?i)<(/?)tr\b"))
        if marker in text[m.start():end]:
            rows.append((m.start(), end))
            pos = end
    return rows


class Board:
    def __init__(self, find, decode):
        self.find, self.decode, self.ready = find, decode, False
        if not DATA.exists():
            return
        d = json.loads(DATA.read_text(encoding="utf-8"))
        self.forums = {int(f["forumid"]): f for f in d.get("forum", [])}
        self.forums[0] = ORPHAN_FORUM
        self.users = {int(u["userid"]): u for u in d.get("user", [])}
        self.threads = {int(t["threadid"]): dict(t, ghost=False) for t in d.get("thread", []) if str(t.get("visible", "1")) != "0"}
        self.posts = {}
        for p in sorted(d.get("post", []), key=lambda p: (int(p.get("dateline") or 0), int(p["postid"]))):
            if str(p.get("visible", "1")) != "0":
                self.posts.setdefault(int(p["threadid"]), []).append(p)
        self.post_thread = {int(p["postid"]): tid for tid, ps in self.posts.items() for p in ps}
        for tid, ps in self.posts.items():
            if tid not in self.threads:
                self.threads[tid] = {"threadid": tid, "forumid": 0, "title": ps[0].get("title") or "（標題未保存）", "ghost": False,
                                     "postusername": ps[0].get("username", ""), "dateline": ps[0].get("dateline"),
                                     "lastpost": ps[-1].get("dateline"), "lastposter": ps[-1].get("username", ""),
                                     "replycount": len(ps) - 1, "views": "", "sticky": 0, "open": 1}
        self.smilies = [(s["smilietext"], s["smiliepath"]) for s in d.get("smilie", []) if s.get("smilietext")]
        self.icons = {int(i["iconid"]): i["iconpath"] for i in d.get("icon", [])}
        settings = {s["varname"]: s.get("value") or "" for s in d.get("setting", [])}
        self.fmt = {k: settings.get(k) or v for k, v in (("dateformat", "m-d-Y"), ("timeformat", "h:i A"), ("registereddateformat", "M Y"))}
        replacements = {r["findword"]: r["replaceword"] for r in d.get("replacement", [])}
        replacements.update(STYLE)
        templates = {t["title"]: t["template"] for t in d.get("template", [])}
        self.postbit = templates.get("postbit", "")
        for k, v in sorted(replacements.items(), key=lambda kv: -len(kv[0])):
            self.postbit = self.postbit.replace(k, v)
        times = [int(x) for t in self.threads.values() for x in (t.get("lastpost"), t.get("dateline")) if str(x or "").isdigit()]
        self.now = max(times) if times else 0
        self.avatars = {}
        self.ready = bool(self.postbit)

    def add_listed(self, rows):
        for tid, row in rows.items():
            if tid not in self.threads:
                self.threads[tid] = dict(row, threadid=tid, ghost=True)

    def adult(self, path, query):
        q = urllib.parse.parse_qs(query)
        if path.endswith("/forumdisplay.php"):
            return q.get("forumid", ["x"])[0].isdigit() and int(q["forumid"][0]) in ADULT_FORUMS
        tid = self.thread_of(q)
        return tid is not None and int(self.threads.get(tid, {}).get("forumid", -1)) in ADULT_FORUMS

    def thread_of(self, q):
        if q.get("threadid", ["x"])[0].isdigit():
            return int(q["threadid"][0])
        if q.get("postid", ["x"])[0].isdigit():
            return self.post_thread.get(int(q["postid"][0]))

    def available(self, path, query):
        q = urllib.parse.parse_qs(query)
        if path.endswith("/forumdisplay.php"):
            return q.get("forumid", ["x"])[0].isdigit() and int(q["forumid"][0]) in self.forums
        if path.endswith("/showthread.php"):
            return self.thread_of(q) in self.posts
        return False

    def shell(self, url):
        s = urllib.parse.urlsplit(url)
        entry = self.find(HOST, s.path, s.query)
        return (self.decode(entry[1].read_bytes()), entry[2], entry[0]) if entry else None

    def forumdisplay(self, fid):
        forum = self.forums[fid]
        shell = self.shell(f"/vbb/forumdisplay.php?s=&forumid={fid}") or self.shell(FORUM_SHELL)
        if not shell:
            return None
        text, url, ts = shell
        rows = outer_rows(text, "showthread.php")
        if not rows:
            return None
        head, tail = self.swap_forum(text[:rows[0][0]], text[rows[-1][1]:], int(re.search(r"forumid=(\d+)", url).group(1)), fid)
        threads = sorted((t for t in self.threads.values() if int(t.get("forumid") or 0) == fid),
                         key=lambda t: (-int(t.get("sticky") or 0), -int(t.get("lastpost") or t.get("dateline") or 0)))
        body = "".join(self.thread_row(t) for t in threads) or \
            '<tr><td bgcolor="#202020" colspan="7" align="center"><font face="新細明體">這個看板的討論串沒有被保存下來。</font></td></tr>'
        return head + body + tail, url, ts

    def swap_forum(self, head, tail, old_fid, new_fid):
        old, new = self.forums.get(old_fid), self.forums.get(new_fid, ORPHAN_FORUM)
        pairs = [(old, new), (self.forums.get(int((old or {}).get("parentid") or -1)), self.forums.get(int(new.get("parentid") or -1)))]
        def swap(s, a, b):
            s = re.sub(rf'forumid={a["forumid"]}(?=["&])', f'forumid={b["forumid"]}', s)
            return s.replace(f'>{a["title"]}<', f'>{html.escape(b["title"])}<').replace(
                f' - {a["title"]}</title>', f' - {html.escape(b["title"])}</title>')
        for a, b in pairs:
            if a and b and a is not b:
                head, tail = swap(head, a, b), swap(tail, a, b)
        return head, tail

    def thread_row(self, t):
        tid, replies = t["threadid"], int(t.get("replycount") or 0)
        views = t.get("views", "")
        hot = replies >= 20 or (str(views).isdigit() and int(views) >= 200)
        folder = ("lock" if str(t.get("open", "1")) == "0" else "") + "folder"
        folder = ("hot" + folder) if hot else folder
        icon = self.icons.get(int(t.get("iconid") or 0))
        last = t.get("lastpost") or t.get("dateline")
        when = (f'{php_date(self.fmt["dateformat"], last)} <font color="#C0C0C0">{php_date(self.fmt["timeformat"], last)}</font>'
                if str(last or "").isdigit() else html.escape(t.get("lastpost_text", "")))
        sticky = '<font face="新細明體">置頂: </font>' if str(t.get("sticky", "0")) == "1" else ""
        return (f'<tr align="center"><td bgcolor="#202020"><img src="images/{folder}.gif" border="0" alt=""></td>'
                f'<td bgcolor="#303030">{f"<img src={chr(34)}{icon}{chr(34)} border=0 alt={chr(34)}{chr(34)}>" if icon else "&nbsp;"}</td>'
                f'<td bgcolor="#202020" align="left" width="70%">{sticky}<font face="新細明體">'
                f'<a href="showthread.php?threadid={tid}">{html.escape(t.get("title") or "")}</a></font></td>'
                f'<td bgcolor="#303030" width="30%" nowrap><font face="新細明體">{html.escape(t.get("postusername") or "")}</font></td>'
                f'<td bgcolor="#202020"><font face="新細明體">{replies}</font></td>'
                f'<td bgcolor="#303030"><font face="新細明體">{html.escape(str(views))}</font></td>'
                f'<td bgcolor="#202020"><table cellpadding="0" cellspacing="0" border="0" width="100%"><tr align="right"><td nowrap>'
                f'<font face="新細明體">{when}<br>by {html.escape(t.get("lastposter") or "")}</font></td></tr></table></td></tr>')

    def showthread(self, tid):
        shell = self.shell(THREAD_SHELL)
        posts = self.posts.get(tid)
        if not shell or not posts or not self.ready:
            return None
        text, url, ts = shell
        anchors = [m.start() for m in re.finditer(r'<a name="post\d+">', text)]
        first = text.rfind(POST_TABLE, 0, anchors[0])
        last = balanced_end(text, text.rfind(POST_TABLE, 0, anchors[-1]), TABLE_TAG)
        body = "".join(self.render_post(p, i) for i, p in enumerate(posts, 1))
        head, tail = text[:first], text[last:]
        thread = self.threads[tid]
        shell_tid = int(re.search(r"threadid=(\d+)", url).group(1))
        titles = {re.search(r"(?is)<title>[^<]*? - (.*?)</title>", head).group(1), self.threads.get(shell_tid, {}).get("title")}
        new_title = html.escape(thread.get("title") or "")
        head, tail = (re.sub(rf"threadid={shell_tid}\b", f"threadid={tid}", s) for s in (head, tail))
        for old in sorted(filter(None, titles), key=len, reverse=True):
            head, tail = head.replace(old, new_title), tail.replace(old, new_title)
        shell_fid = re.search(r"newthread\.php\?[^\"]*forumid=(\d+)", head)
        if shell_fid:
            head, tail = self.swap_forum(head, tail, int(shell_fid.group(1)), int(thread.get("forumid") or 0))
        return head + body + tail, url, ts

    def ghost_item(self, tid):
        t = self.threads[tid]
        when = lambda ts: f'{php_date(self.fmt["dateformat"], ts)} {php_date(self.fmt["timeformat"], ts)}' if str(ts or "").isdigit() else ""
        return {"title": t.get("title") or "（無標題）", "author": t.get("postusername", ""), "time": when(t.get("dateline")),
                "views": t.get("views"), "replies": t.get("replycount"), "last": when(t.get("lastpost")) or t.get("lastpost_text", "")}

    def decorate_index(self, text):
        orphans = sum(1 for t in self.threads.values() if int(t.get("forumid") or 0) == 0)
        link = (f'<p align="center"><font face="新細明體"><a href="forumdisplay.php?forumid=0">其他存到的文章'
                f'（{orphans} 個討論串，看板不明）</a></font></p>')
        return re.sub(r"(?i)</body>", link + "</body>", text, count=1) if orphans else text

    def render_post(self, p, index):
        user = self.users.get(int(p.get("userid") or 0), {"username": p.get("username", ""), "posts": 0})
        icon = self.icons.get(int(p.get("iconid") or 0))
        values = {"postid": p["postid"], "userid": p.get("userid", ""), "username": html.escape(user.get("username") or p.get("username", "")),
                  "usertitle": html.escape(user.get("usertitle") or ""), "posts": user.get("posts", ""),
                  "joindate": php_date(self.fmt["registereddateformat"], user["joindate"]) if str(user.get("joindate", "")).isdigit() else "",
                  "backcolor": STYLE["{firstaltcolor}"] if index % 2 else STYLE["{secondaltcolor}"],
                  "icon": f'<img src="{icon}" border="0" alt="">' if icon else "", "title": html.escape(p.get("title") or ""),
                  "message": bbcode(p.get("pagetext") or "", self.smilies if str(p.get("allowsmilie", "1")) == "1" else []),
                  "postdate": php_date(self.fmt["dateformat"], p["dateline"]), "posttime": php_date(self.fmt["timeformat"], p["dateline"]),
                  "avatar": self.avatars.get(int(p.get("userid") or 0), "")}
        scalars = {"countposts": index, **rpg(user, self.now)}

        def var(m):
            if m.group(1) == "post":
                return str(values.get(m.group(2), ""))
            return "" if m.group(2) else str(scalars.get(m.group(1), ""))
        return re.sub(r"\$([a-zA-Z_]+)(?:\[([a-zA-Z_0-9]+)\])?", var, self.postbit)

    def listed_rows(self):
        found = {}
        for fid in self.forums:
            shell = self.shell(f"/vbb/forumdisplay.php?s=&forumid={fid}")
            if not shell:
                continue
            for start, end in outer_rows(shell[0], "showthread.php"):
                row = shell[0][start:end]
                cells = re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", re.sub(r"(?s)<!--.*?-->", "", row))
                tid = re.search(r"threadid=(\d+)", row)
                text = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip() for c in cells]
                if not tid or len(text) < 6:
                    continue
                title = re.findall(r'(?is)<a href="showthread\.php\?[^"]*threadid=\d+"[^>]*>(.*?)</a>', row)
                found[int(tid.group(1))] = {
                    "forumid": fid, "title": html.unescape(re.sub(r"<[^>]+>", "", title[-1])).strip() if title else "",
                    "postusername": text[3], "replycount": text[4] if text[4].isdigit() else 0, "views": text[5],
                    "sticky": 1 if "置頂" in row else 0, "lastpost_text": text[6] if len(text) > 6 else "",
                    "lastposter": (re.findall(r"by\s+(.+)$", text[6]) or [""])[0] if len(text) > 6 else "", "open": 0 if "lock" in row else 1,
                    "lastpost": parse_vb_time(text[6]) if len(text) > 6 else None}
        return found
