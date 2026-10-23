# Handoff：cgany 模擬復活計畫

寫給接手的 Claude Code（在 WSL 裡跑）。之前的工作是在 Windows 上做的，那邊的記憶你讀不到，需要知道的都寫在這裡。開始前請先讀 `README.md` 和 `docs/ARCHITECTURE.md`。

## 目前狀態（2026-10-22）

- **Wayback 下載已全部完成**，不用再爬，也不要重新查 CDX。itaiwan 的 `/phpadm/` 和 `/vbb/member.php` 也在 2026-10-23 補抓完了：phpadm 4,316 / 4,351 頁（剩下 35 頁重試後仍是 404），member.php 1,055 / 1,055 頁。
- **公開 repo**：`lineage8025/cgany-revival`（使用者 2026-10-22 決定公開；commit 一律用 noreply 信箱，見下方「Git 和 GitHub」）。Windows 那邊另有一份 clone 在 `%USERPROFILE%\cgany-revival\`。
- **架構分析**已完成，見 `docs/ARCHITECTURE.md`。
- **已開給夥伴試看**（2026-10-23）：<https://cgany.loveloli.org>，經 Cloudflare Tunnel `cgany-revival`；2026-10-23 起改跑在使用者的 OCI VM（ARM，ssh 別名見本機 `.env` 的 `DEPLOY_HOST`），本機的容器已停用但保留，更新用 `tools/deploy.sh`＋Access application `cgany-revival`（Everyone、One-time PIN、session 168h）。管理用的 Cloudflare API token 在本機 `~/.config/cloudflare/cgany.env`，tunnel token 在 repo 的 `.env`，兩者都不進版控。切到公開模式後，本機的 `*.localhost` 網址不再適用，一律走公開網址。
- **公開模式**：`.env` 設 `BASE_DOMAIN`（預計 `cgany.loveloli.org`、`SUBDOMAIN_SEP=-`）就切換，部署方式見 `README.md` 的「公開部署」。使用者決定：子網域模式、成人區的圖片全部遮掉，進入前的確認頁用原站 `warning.htm` 的外觀、內文改成分級標示與條款、公告不留信箱、改請大家到 repo 開 issue、圖片都已不在所以不另做版權移除聲明。架設位置還沒決定；先開給夥伴試看時，用 Cloudflare Tunnel＋Access（Include Everyone、One-time PIN 登入，2026-10-23 決定）。
- **第一版本機瀏覽**已完成：`revive/server.py`，在 WSL 用 `docker compose up -d --build` 啟動，用法見 `README.md` 的「本機瀏覽」。它在送出頁面時才轉碼、改寫連結，原始資料不動，所以原本第 2、3 步（Big5 轉 UTF-8、連結改寫）已經涵蓋。

## 資料位置（都在 Windows 的 C 槽，不在 repo 裡）

| 內容 | Windows 路徑 | WSL 路徑 |
|---|---|---|
| cgany.itaiwan.net（799 頁） | `%USERPROFILE%\cgany_archive\` | `/mnt/c/Users/<帳號>/cgany_archive/` |
| cgany.com 全部子網域（23,457 頁） | `%USERPROFILE%\cgany_com_archive\` | `/mnt/c/Users/<帳號>/cgany_com_archive/` |
| 網址清單、CDX 索引、抓不到的清單 | `%USERPROFILE%\cgany_crawl\` | `/mnt/c/Users/<帳號>/cgany_crawl/` |

**請把這三個資料夾當作唯讀的原始資料。** 衍生出來的東西（轉碼、解析結果、重建的網站）請另外放，建議 `/mnt/c/Users/<帳號>/cgany_build/`，或者放在 WSL 的家目錄。

### 檔案格式

- **頁面**：原始位元組，大多是 **Big5**。
  - 解碼建議用 `cp950` 或 `big5hkscs` 加上 `errors="replace"`。純 `big5` 遇到擴充字會失敗。
  - 2016 年以後的 WordPress 頁面是 UTF-8，但那些不是原站內容。
- **檔名規則**：
  - cgany.com 的頁面放在 `raw/<host>/<path>`。
  - itaiwan 的頁面沒有 host 這一層，直接放在 `raw/<path>`。
  - 網址以 `/` 結尾的存成 `index.html`。
  - 有 query 的，檔名是「路徑 + `__` + query」，query 裡 `[A-Za-z0-9=&._-]` 以外的字元都換成 `_`。例如 `raw/cg.cgany.com/bbs.pl__act=click&file=20041123095018`。
  - 寫不進去的（檔案和資料夾撞名）放在 `raw/_flat/`。
  - **查檔案請一律用索引檔，不要自己從網址推檔名。**
- **索引檔**：
  - itaiwan 是 `index.tsv`，cgany.com 是 `index_a.tsv` 加 `index_b.tsv`，兩個合起來才是全部。
  - 每行四欄，用 tab 分隔：原始網址、Wayback 時間戳、相對於該資料夾的本機路徑（Windows 反斜線）、Wayback 網址。
  - 原始網址可能帶 `:80`，例如 `http://hcg.cgany.com:80/bbs.pl?...`。
- **`cgany_crawl/` 裡的檔案**：

  | 檔案 | 說明 |
  |---|---|
  | `targets_com.txt` | 23,768 個目標，空白分隔：時間戳、網址、MIME、狀態、長度、urlkey |
  | `cdx_cgany_com.txt` | cgany.com 的完整 CDX，63,122 筆，含 404 和轉址 |
  | `cdx_cgany_itaiwan.txt` | itaiwan 的完整 CDX，6,722 筆 |
  | `missing.txt` | 抓不到的 311 頁 |

### 各網域的頁數

| 網域 | 頁數 | 備註 |
|---|---|---|
| hcg.cgany.com | 11,939 | 成人板 |
| cg.cgany.com | 4,601 | |
| do.cgany.com | 2,757 | |
| bbs.cgany.com | 1,286 | phpBB 和 Coppermine |
| cgany.com | 1,165 | 幾乎都是 2020 年以後的 WordPress，不是原站 |
| test.cgany.com | 926 | |
| acg.cgany.com | 647 | |
| www.cgany.com | 423 | |
| 其他 | 少量 | |

## 使用者已經做的決定（不要推翻）

1. **抓下來的頁面不能進 repo，任何一頁都不行。** hcg 是成人 CG 板，即使是私人 repo，GitHub 規範也不允許，有停權風險。repo 只放程式碼、工具和文件。`.gitignore` 已經擋了 `raw/` 和 `*.tsv`；如果你產生了新的資料檔（JSON、SQLite、轉碼後的 HTML），**也要放在 repo 外面，或者加進 `.gitignore`**。
2. **itaiwan 的 `/phpadm/` 和 `/vbb/member.php` 在 2026-10-22 依使用者指示全部補抓。**
   - `/phpadm/` 是站長沒上鎖的 phpMyAdmin，共 4,351 頁，其中 `sql.php` 是瀏覽資料表的頁面，可能有 vBulletin 的文章內容。
   - `member.php` 是會員資料頁，共 1,055 頁。
   - 檔案放在 `cgany_archive/raw/cgany.itaiwan.net/...`，有 host 這一層，跟早期抓的 itaiwan 頁面不同。
   - 索引檔是 `index_phpadm_a.tsv`、`index_phpadm_b.tsv`、`index_vbbmember.tsv`。
   - 這些頁面含當年會員的 email、密碼雜湊、IP 等個資。**只能在本機使用；如果復活的網站要公開，必須先拿掉這些欄位。**
   - **`member.php` 全部都是「請先登入」頁**，沒有會員資料，可以忽略。
   - **phpadm 能還原的資料**：`sql.php` 頁面全部都是 `pos=0`，也就是每頁只有前 30 筆。但爬蟲點過每個欄位的排序（ORDER BY 各欄 ASC/DESC），加上 24 種語系版本，所以把所有頁面的列合併、以主鍵去重後，能拼出的筆數如下（另有 2002–2003 年不同時間的快照，同一筆內容可能不同）：

     | 資料表 | 可還原筆數 | 當時總筆數 |
     |---|---|---|
     | thread | 534 | 3,403 |
     | post | 430 | 39,359 |
     | user | 383 | 2,343 |
     | privatemessage | 321 | 789 |
     | template | 179 | 497 |
     | pollvote / userfield / subscribethread | 160–173 | 約 2,000–3,000 |
     | forum、moderator、forumpermission、usergroup、icon、smilie、bbcode、setting、settinggroup、announcement 等設定表 | **全部** | — |

     也就是說，版面結構（看板、權限、表情符號、樣板）可以完整重建，文章只剩約 1%。另外有 `primary_key=...` 的單筆頁面（post 30 筆、user 28 筆），內容較完整。
   - vBulletin 的文章本體（`showthread.php`）在 Wayback 上幾乎沒有存檔；`/newvbb/` 只有 2002-02 的首頁一頁，其他都是 404。
   - **已重建 vBulletin 交流區**（2026-10-23）：`tools/vbb_extract.py` 把上述資料（去除個資、不含私人訊息）輸出成 `cgany_build/vbb/vbb.json`，`revive/vbb.py` 依此產生看板頁與文章頁，用法見 README。載入後共 32 個看板（含「其他存到的文章」）、885 個討論串、430 篇文章。

## 已知的坑

- **Wayback 會限速。** 穩定的設定是兩個程序、每個請求間隔 1.2 秒，大約每分鐘 18 頁。開更多程序可能被暫時封 IP。
- **Big5 中文 query 的網址**：CDX 的 `original` 欄位會變亂碼，要改用 `urlkey` 重組網址。`tools/crawl2.py` 已經處理了。
- **`missing.txt` 那 311 頁**在 Wayback 上永久是 404，換其他時間點的存檔也一樣，不用再試。
- **圖片幾乎都是外連**（myweb.hinet.net、geocities.jp、pchome、groups.msn.com 等），這次沒抓。要找回來得另外查各圖床在 Wayback 的存檔。
- **2010 年以後的貼圖板腳本改成亂碼檔名**，同一個板會有好幾個腳本名，例如 hcg 有 `bbs.pl`、`bbs7.pl`、`b38vcyfew339vsi.pl`、`fgew7fg3w83.pl`。合併資料時要把它們視為同一個板。
- **同一篇文章可能有好幾份存檔**（不同腳本名、itaiwan 和 cgany.com 各一份）。以文章 ID 加板名去重。
- **2016 年以後 cgany.com 的 WordPress 頁面**都不是原站內容，重建時請排除。

## Git 和 GitHub

- WSL 裡要先登入 GitHub（`gh auth login`），再 `gh repo clone lineage8025/cgany-revival`，建議 clone 到 WSL 家目錄。程式要讀的資料走 `/mnt/c/...`。
- **不要同時在 Windows 那份 clone 和 WSL 這份 clone 裡改東西**，會衝突。動手前先 `git pull`。
- commit 作者：repo 已公開，一律用 noreply 信箱 `lineage8025 <43869731+lineage8025@users.noreply.github.com>`。WSL 這份 clone 已在 repo 層級設定（`git config --local`）；新 clone 要自己設一次。
- 換行規則寫在 `.gitattributes`：`.bat` 檔固定用 CRLF，其他檔案由 git 自動處理。

## 建議的下一步（照順序）

0. **公開前的風險處理（2026-10-23）**。repo 已公開；預覽站仍有 Cloudflare Access email 驗證（使用者決定保留）。以下是為了把著作權和個資風險壓低：
   - ~~全部板都遮圖~~：**使用者 2026-10-23 改決定：只有成人區遮圖，其他板維持外站圖片照常顯示，不要改成全部遮。**（外站圖片是由瀏覽器向原本的圖床載入；`WAYBACK_EXTERNAL` 預設關閉，不會向 Wayback 載入。）
   - **確認個資頁不外流**（已完成）：公開模式下程式強制關閉 `PRIVATE_PAGES`，設定檔誤開也無效；email 一律遮成 `x***@domain`。
   - **下架聲明**（已完成 2026-10-23）：首頁公告加了【下架聲明】，並有下架清單 `override/takedown.txt`，用法見 README。
   - **成人板文字抽查**：抽查 hcg 等成人板的標題和內文，如果有描述未成年人性內容的文字，要先回報使用者，由使用者決定該板要不要公開，或是只公開列表。
1. **貼圖板解析器**：讀索引檔，把所有 `act=click` 的文章頁解析成結構化資料。欄位：板名、文章 ID、主題、作者、發表時間、內文 HTML、圖片網址、回應列表（作者、時間、內容）、來源檔案、Wayback 時間戳。輸出成 SQLite 或 JSONL，放在 repo 外面。先拿 `cg.cgany.com` 的幾百頁試，確認格式穩定後再跑全部。不同年代的版面可能略有差異，請抽樣 2001、2004、2008、2011 年的頁面各看幾頁。
2. **補列表頁**：`revive/server.py` 已用存檔列表當樣板重建各板列表與翻頁（`render_list`），資料來自文章頁的「主題／時間／作者」與回應時間。還沒做的：每個板只用一份樣板（不會隨年代換外觀）、人氣數多半是空的、搜尋沒有重建；完整的解析器（第 1 步）可以補齊這些。
3. **（選做）外連圖片**：第一版已經讓瀏覽器即時向 Wayback 拿外站圖片。要離線也看得到，再統計圖片網址的網域分佈，挑幾個大宗圖床查 Wayback 的命中率，決定要不要大規模抓。抓的時候一樣要遵守限速。
4. **（選做）phpBB 和 Coppermine**：看使用者想要原汁原味（Docker 架 PHP 4 和同版本軟體）還是輕量（第一版已經能直接展示存檔頁）。

每完成一步，請更新 `README.md` 的待辦清單和這份 HANDOFF。
