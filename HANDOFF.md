# Handoff：cgany 模擬復活計畫

寫給接手的 Claude Code（在 WSL 裡跑）。之前的工作是在 Windows 上做的，那邊的記憶你讀不到，需要知道的都寫在這裡。開始前請先讀 `README.md` 和 `ARCHITECTURE.md`。

## 目前狀態（2026-10-22）

- **Wayback 下載已全部完成**，不用再爬，也不要重新查 CDX。唯一的例外是 itaiwan 的 `/phpadm/` 和 `/vbb/member.php`，2026-10-22 晚上在 Windows 那邊補抓中。如果它們的索引檔行數不到 4,351 和 1,055，代表還沒跑完或中斷了，可以用 `tools/crawl2.py` 加 `cgany_crawl/` 裡的 `tp_a.txt`、`tp_b.txt`、`targets_vbbmember.txt` 續跑。
- **私人 repo**：`lineage8025/cgany-revival`。Windows 這邊已經有一份 clone 在 `C:\Users\Michael\cgany-revival\`，目前只有工具和文件。
- **架構分析**已完成，見 `ARCHITECTURE.md`。
- **還沒開始**寫任何復活用的程式。

## 資料位置（都在 Windows 的 C 槽，不在 repo 裡）

| 內容 | Windows 路徑 | WSL 路徑 |
|---|---|---|
| cgany.itaiwan.net（799 頁） | `C:\Users\Michael\cgany_archive\` | `/mnt/c/Users/Michael/cgany_archive/` |
| cgany.com 全部子網域（23,457 頁） | `C:\Users\Michael\cgany_com_archive\` | `/mnt/c/Users/Michael/cgany_com_archive/` |
| 網址清單、CDX 索引、抓不到的清單 | `C:\Users\Michael\cgany_crawl\` | `/mnt/c/Users/Michael/cgany_crawl/` |

**請把這三個資料夾當作唯讀的原始資料。** 衍生出來的東西（轉碼、解析結果、重建的網站）請另外放，建議 `/mnt/c/Users/Michael/cgany_build/`，或者放在 WSL 的家目錄。

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
- commit 作者請設成和之前一樣，用 noreply 信箱，避免公開使用者的真實 email：
  ```
  git config user.name lineage8025
  git config user.email 43869731+lineage8025@users.noreply.github.com
  ```
- 換行規則寫在 `.gitattributes`：`.bat` 檔固定用 CRLF，其他檔案由 git 自動處理。

## 建議的下一步（照順序）

1. **貼圖板解析器**：讀索引檔，把所有 `act=click` 的文章頁解析成結構化資料。欄位：板名、文章 ID、主題、作者、發表時間、內文 HTML、圖片網址、回應列表（作者、時間、內容）、來源檔案、Wayback 時間戳。輸出成 SQLite 或 JSONL，放在 repo 外面。先拿 `cg.cgany.com` 的幾百頁試，確認格式穩定後再跑全部。不同年代的版面可能略有差異，請抽樣 2001、2004、2008、2011 年的頁面各看幾頁。
2. **Big5 轉 UTF-8**：把靜態頁（FrontPage 入口、`rule.txt` 等）轉成 UTF-8，同時把 `<meta charset>` 改成 UTF-8。
3. **連結改寫**：把頁面裡指向 `cgany.com` 各子網域、`cgany.itaiwan.net` 的絕對和相對網址，對應到本機重建後的路徑。找不到的頁面要有明確標示，不要變成空白頁。
4. **仿製版貼圖板**：做一個小型網站（靜態產生或本機伺服器都可以），重現列表、文章頁、翻頁、各板切換、首頁入口，外觀沿用存檔的 HTML 和 CSS。
5. **（選做）外連圖片**：統計圖片網址的網域分佈，挑幾個大宗圖床查 Wayback 的命中率，再決定要不要大規模抓。抓的時候一樣要遵守限速。
6. **（選做）phpBB 和 Coppermine**：看使用者想要原汁原味（Docker 架 PHP 4 和同版本軟體）還是輕量（直接展示存檔頁）。

每完成一步，請更新 `README.md` 的待辦清單和這份 HANDOFF。
