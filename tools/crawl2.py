import os, re, sys, time, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

targets, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
index_path = os.path.join(outdir, sys.argv[3] if len(sys.argv) > 3 else "index.tsv")
done = set()
if os.path.exists(index_path):
    with open(index_path, encoding="utf-8") as f:
        done = {line.split("\t")[0] for line in f}

def local_name(url):
    host = re.match(r"^https?://([^/:]+)", url).group(1)
    path = re.sub(r"^https?://[^/]+", "", url) or "/"
    if path.endswith("/"):
        path += "index.html"
    path, _, query = path.partition("?")
    name = path.lstrip("/")
    if query:
        name += "__" + re.sub(r"[^A-Za-z0-9=&._-]", "_", query)
    name = re.sub(r'[<>:"|*]', "_", name)
    return os.path.join(host, name.replace("/", os.sep))

lines = [l.split() for l in open(targets, encoding="utf-8") if l.strip()]
with open(index_path, "a", encoding="utf-8") as idx:
    for i, (ts, url, mime, status, *rest) in enumerate(lines, 1):
        if url in done:
            continue
        fetch = url
        if not url.isascii() and rest:
            # Big5 query strings come back garbled in "original"; the urlkey keeps them percent-encoded
            fetch = re.match(r"^https?://[^/]+", url).group(0) + rest[-1].split(")", 1)[1]
        wb = f"https://web.archive.org/web/{ts}id_/{fetch}"
        dest = os.path.join(outdir, "raw", local_name(fetch))
        for attempt in range(6):
            try:
                with urllib.request.urlopen(wb, timeout=60) as r:
                    data = r.read()
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(10 * (attempt + 1))
                    continue
                data = None
                print(f"[{i}/{len(lines)}] HTTP {e.code} {url}", flush=True)
                break
            except Exception as e:
                time.sleep(10 * (attempt + 1))
        else:
            data = None
            print(f"[{i}/{len(lines)}] GAVE UP {url}", flush=True)
        if data is not None:
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(data)
            except OSError:
                dest = os.path.join(outdir, "raw", "_flat", re.sub(r"[^A-Za-z0-9=&._-]", "_", url)[:200])
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(data)
            idx.write(f"{url}\t{ts}\t{os.path.relpath(dest, outdir)}\t{wb}\n")
            idx.flush()
            if i % 50 == 0:
                print(f"[{i}/{len(lines)}] ok", flush=True)
        time.sleep(1.2)
print("DONE", flush=True)
