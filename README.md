# cgany 模擬復活計畫

用 Internet Archive（Wayback Machine）的存檔，在本機重建已關站的台灣早期 CG 論壇 cgany（2001–2011），讓它能像當年一樣離線瀏覽。

## 資料（不放在這個 repo）

抓下來的頁面只留在本機，不會進版控：

| 來源 | 頁數 | 本機位置 |
|---|---|---|
| cgany.itaiwan.net（2001–2003） | 799 | `<DATA>\cgany_archive\` |
| cgany.com 全部子網域（2003–2011 為主） | 23,457 / 23,768 | `<DATA>\cgany_com_archive\` |
| 網址清單、Wayback CDX 索引、抓不到的 311 頁清單 | — | `<DATA>\cgany_crawl\` |

- `<DATA>` 是存放資料的目錄，在 `.env` 的 `CGANY_DATA` 指定它在 Docker 主機上的路徑。
- 頁面是 Big5 原始檔，存在 `raw\<子網域>\...`，對照表是 `index*.tsv`（原始網址、存檔時間、本機檔案、Wayback 網址）。
- 抓不到的 311 頁在 Wayback 上一律回 404，幾乎都是 2010–2011 年的留言板文章。

## 本機瀏覽（第一版）

用 Docker 啟動（任何能跑 Docker Compose 的環境都行，例如 Linux、macOS、Windows 的 WSL 或 Docker Desktop、NAS），把存檔頁依原始網址放出來：

```bash
docker compose up -d --build     # 啟動（第一次或改過程式後要 --build）
docker compose logs -f revive    # 看 log
docker compose down              # 停止
```

開瀏覽器到 <http://localhost:8000/>，首頁列出所有網域。兩種瀏覽方式：

| 模式 | 網址範例 | 說明 |
|---|---|---|
| 子網域 | `http://www.cgany.com.localhost:8000/` | 原始網域後面加 `.localhost`，最接近當年 |
| 路徑 | `http://localhost:8000/_/www.cgany.com/` | 瀏覽器不支援 `*.localhost` 時用 |

- 頁面送出時才轉成 UTF-8 並改寫連結，原始資料不會被修改。
- 指向 cgany 各網域的連結會改成本機網址。外站連結預設先導到「你進黑洞啦！」提示頁，可以從那裡選擇仍要前往原網址；設 `WAYBACK_EXTERNAL=1` 則外站圖片和連結直接改走 Wayback（見下表）。
- 本機沒有存檔的頁面、送出表單（投票、發文）、會員個資頁，都會顯示「你進黑洞啦！」提示頁並說明原因。存檔頁面裡指向缺頁的連結會變淡，滑鼠移上去顯示「本機沒有存檔」。
- 貼圖板的列表頁（含翻頁）是重建的：沿用該板存得最完整的一份列表當外觀，填入本機存到的全部文章，依發表時間由新到舊。Wayback 只存到列表、沒存到內文的文章也會列出（連結變淡），點進去是「這篇文章沒能留下來」的說明頁，附當年列表記下的主題、作者、時間、人氣與回應數。回應數和最後回應時間從文章頁算出；人氣只有在某份列表快照出現過的文章才有數字。頁碼選單依年份分組並標出每頁的日期範圍；搜尋列多了年份選單，可依作者或主題關鍵字、年份篩選。
- 首頁的「各板文章總覽」用年份分頁列出同樣的文章，另外也列出內容不完整的存檔。啟動後約 30 秒建好，建好之前列表頁會先顯示 Wayback 的原始快照。
- 貼圖板裡 2010–2012 年灌進來的廣告文（藥品、保險、亂碼主題）會從列表頁和總覽隱藏，文章本身仍能用網址打開。
- 2013 年以後的存檔一律排除：2013–2014 年是網域停放的廣告頁，2016 年以後是網域被接手後的 WordPress。
- 只綁 `127.0.0.1`，區網連不到。

**自己補檔案**：放在 `<DATA>\cgany_build\override\<網域>\<路徑>` 的檔案會優先於存檔，原始資料不用動。

音樂播放器：把歌曲用歌名當檔名放進 `override\www.cgany.com\music\`（例如 `くじびきアンバランス.mp3`，全形半形、大小寫、空白不影響比對），有檔案的歌會排在歌單最前面（原歌單沒有的歌也會加進來），後面接原歌單其他的歌。播放器只在有檔案的歌之間輪播；在 LIST 點到沒有檔案的舊歌，3 秒後會跳回第一首。資料夾裡一首都沒有時維持原歌單的行為。支援 mp3、m4a、aac、ogg、opus、flac、wav、webm。播放器原本靠 Windows Media Player 外掛，伺服器會自動把它換成 HTML5 `<audio>`。加歌後重新整理即可，不用重啟容器。

存檔裡的執行檔與壓縮檔（例如首頁「解除色情守門員限制」連到的 `godie.rar`，內含來源不明的 `u.exe`）一律不提供下載，連結保留、點了顯示說明頁。

設定用環境變數或 repo 根目錄的 `.env`：

| 變數 | 預設 | 說明 |
|---|---|---|
| `CGANY_DATA` | （必填） | `<DATA>` 在 Docker 主機上的路徑，例如 WSL 的 `/mnt/c/Users/<帳號>`、Linux 的 `/srv/cgany`、Synology 的 `/volume1/cgany` |
| `CGANY_PORT` | `8000` | 本機連接埠 |
| `WAYBACK_EXTERNAL` | `0` | `1` 時外站圖片和連結改走 Wayback。每開一篇文章，瀏覽器就會向 Wayback 發出好幾個請求，和下載程式同時跑容易被暫時封 IP |
| `PRIVATE_PAGES` | `0` | `1` 時開放 itaiwan 的 `/phpadm/` 和 `/vbb/member.php`（含會員個資，只限本機） |

### vBulletin 交流區（itaiwan `/vbb/`，2001–2003）

存檔裡的 phpMyAdmin 頁面可以拼回當年 vBulletin 論壇的部分資料庫，`revive/vbb.py` 用它重建交流區：

1. 先跑 `python3 -I tools/vbb_extract.py`，產出 `<DATA>\cgany_build\vbb\vbb.json`（在 repo 外面）。只保留看板、討論串、文章與會員的暱稱、頭銜、加入日期、發文數；email、IP、密碼與私人訊息一律不輸出。
2. 伺服器啟動時讀這個檔案（`compose.yaml` 已掛載），沒有這個檔案就維持只放存檔頁。

- 論壇首頁用存檔頁，底下多一個「其他存到的文章」入口，收看板不明的討論串。
- 看板頁用存檔頁當外殼，列出資料庫與存檔列表裡的全部討論串；文章頁有存檔就用存檔，沒有就用資料庫裡的 `postbit` 樣板重組，包含當年 RPG 外掛的等級與 HP／MP／Exp。
- 只剩標題的討論串顯示「這篇文章沒能留下來」；「18禁 For 幻夢之星」看板比照成人區處理。

## 公開部署

在 repo 根目錄建 `.env`（照 `.env.example`，`.env` 不會進版控）：

```bash
BASE_DOMAIN=cgany.loveloli.org
SUBDOMAIN_SEP=-
```

設了 `BASE_DOMAIN` 就是公開模式：

| 原始網域 | 公開網址（`SUBDOMAIN_SEP=-`） | 公開網址（留空，用點） |
|---|---|---|
| `cgany.com` / `www.cgany.com` | `cgany.loveloli.org`、`www-cgany.loveloli.org` | `cgany.loveloli.org`、`www.cgany.loveloli.org` |
| `cg.cgany.com` 等子網域 | `cg-cgany.loveloli.org` | `cg.cgany.loveloli.org` |
| `cgany.itaiwan.net` | `itaiwan-cgany.loveloli.org` | `itaiwan.cgany.loveloli.org` |

- 用點的寫法是兩層子網域，Cloudflare 免費的 Universal SSL 只涵蓋一層（`*.loveloli.org`），要另外買 Advanced Certificate；用連字號就不用。
- 成人區（hcg、itaiwan 的 `/hcg/`、www 的 `/hcg/`、`/q7q7/`）不論本機或公開：
  - 進入前先顯示確認頁：外觀是原站的 18 禁警告頁，內文改成「本網站已依網站內容分級規定處理」的分級標示與條款；同意後 30 天內不再問（`AGE_GATE=0` 可關）。
  - 文章裡的圖片一律遮成「（圖片已隱藏）」，連到圖檔的連結也拿掉，只留文字。
- 公開模式另外會自動：頁面裡的 email 遮成 `a***@gmail.com`；強制關閉會員個資頁；關閉路徑模式。
- 文章總覽在任一子網域的 `/__archive/`。

部署在另一台主機時（例如雲端 VM）：在那台 clone 這個 repo、把資料夾複製過去、建好它自己的 `.env`（`CGANY_DATA` 改成那台的路徑，tunnel token 用同一個），之後在本機執行 `tools/deploy.sh` 就會：同步 `cgany_build`（override 與 vBulletin 資料，以本機為準，本機刪掉的檔案那邊也會刪）、在那台 `git pull` 並重新建置、重啟。存檔資料有變動時加 `--data`。腳本要求程式改動已經 commit 並 push。

**下架清單**：`<DATA>/cgany_build/override/takedown.txt` 一行一個網址（原站或公開網址皆可，`#` 為註解）。命中的頁面回「此內容已移除」（HTTP 410），貼圖板列表、搜尋、文章總覽與 vBulletin 看板也會一起拿掉；貼圖板以「板＋文章編號」比對，vBulletin 可指定整個討論串（`threadid=`）或單篇（`postid=`）。檔案改了會自動重新讀取，用 `tools/deploy.sh` 同步即可。

**不讓搜尋引擎收錄**：每個子網域的 `/robots.txt` 都回「全部禁止」，每個回應也帶 `X-Robots-Tag: noindex, nofollow, noarchive`；要讓搜尋引擎收錄時設 `NOINDEX=0`。

**存取紀錄**：網站會把每個請求記到 `<DATA>/logs/access-YYYY-MM-DD.log`（時間、訪客 IP、國家、Cloudflare Access 登入信箱、網址、狀態碼），超過 30 天自動刪除（`ACCESS_LOG_DAYS` 可改）；`docker logs` 裡不含這些個資。資料夾要先建好並讓容器的 UID 65534 寫得進去（例如 `sudo chown 65534:65534 <DATA>/logs`），沒有就不記。`tools/report.sh [天數]` 會在部署主機上彙總：每位訪客看了幾頁、看了哪些、最常被看的頁面。
## 文件

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)：原站的技術架構分析
- [`docs/HANDOFF.md`](docs/HANDOFF.md)：交接說明，給接手的人或 agent 看
- [`docs/PLAN-6.0.md`](docs/PLAN-6.0.md)：模擬CG美少女 6.0（可發文的新站）規劃草案

## 工具

| 檔案 | 說明 |
|---|---|
| `tools/crawl2.py` | 從 Wayback 下載清單裡的頁面，可中斷續跑：`python -I crawl2.py <清單> <輸出資料夾> <索引檔名>` |
| `tools/resume.bat` | 用兩個程序續跑 cgany.com 的下載 |
| `revive/server.py` | 本機存檔伺服器，由 `compose.yaml` 啟動 |

## 待辦

- [x] 把 Big5 轉成 UTF-8（伺服器送出時轉）
- [x] 改寫頁面裡的連結，指向本機檔案（`bbs.pl?act=click&file=...` 這類 CGI 網址要對應到存檔檔名）
- [x] 做一個本機伺服器或靜態網站，能從首頁一路點進各板和文章
- [ ] 解析貼圖板文章，整理各板的文章列表與索引頁（Wayback 沒存到的列表頁用已抓到的文章重建）
- [x] 標示抓不到的頁面，避免點了是空白
