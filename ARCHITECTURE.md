# cgany 原站架構分析

這份分析根據兩種來源：

- **Wayback 保留的原始 HTTP 標頭**（`x-archive-orig-server`、`x-archive-orig-x-powered-by`、`x-archive-orig-set-cookie`）
- **已抓下來頁面裡的軟體簽名**（`Powered by`、`<meta name="generator">`、cookie 名稱）

伺服器端的程式碼和資料庫都沒有被存檔，只能從輸出的 HTML 反推。

## 技術演進

| 時期 | 位置 | 伺服器 | 軟體 |
|---|---|---|---|
| 2001 | cgany.itaiwan.net | Apache 1.3.12、OpenSSL 0.9.6a、PHP 4.0.4pl1 | `/cg/bbs.pl`：Perl CGI 貼圖板；`/bbs/leoboard.cgi`：LeoBBS（雷傲論壇，Perl） |
| 2001–2003 | cgany.itaiwan.net | Apache 1.3.27、OpenSSL 0.9.6i、PHP 4.3.0、mod_throttle 3.1.2 | `/vbb/`：vBulletin 2.2.1 → 2.2.6（PHP＋MySQL）；`/phpadm/`：phpMyAdmin（沒上鎖） |
| 2003–2008 | cgany.com | 這段沒取到標頭 | 一個板一個子網域（cg、hcg、do、test、acg），各自跑同一套 Perl 貼圖板 `bbs.pl`；www 首頁是 Microsoft FrontPage 4/5/6 做的框架式靜態頁 |
| 2005 | bbs.cgany.com | Apache 2.0.46（Red Hat）、PHP 4.3.2 | phpBB 2.0.8 → 2.0.11（cookie `phpbb2mysql_*`）；Coppermine 1.3.2 相簿（`/cpg/`，cookie `cpg132_data`） |
| 2010–2014 | 各子網域 | Microsoft-IIS 7.5 | 還是同一套 Perl 貼圖板，但腳本改成亂碼檔名，例如 `crismh3cg.pl`、`b38vcyfew339vsi.pl`、`fgew7fg3w83.pl`，推測是為了擋機器人和外連 |
| 2017 | www.cgany.com | Microsoft-IIS 7.5、ASP.NET | 不明 |
| 2020–2026 | cgany.com | Cloudflare | WordPress 5.7 → 6.9、Elementor、Astra 佈景；內容是 AI 和 TikTok 之類的文章，**應該是網域被別人接手，跟原站無關** |

## 各子系統

### 1. Perl 貼圖板 `bbs.pl`（主體，約 2 萬頁）

- 每個板一個子網域：`cg.`（CG 貼圖區）、`hcg.`（成人 CG）、`do.`、`acg.`、`test.`（貼圖測試區）。itaiwan 時期是同站的子目錄（`/cg/`、`/do/`、`/test/`、`/hcg/`）。
- 頁面上沒有任何作者或版本資訊，原始碼拿不到。
- **網址格式**

  | 網址 | 用途 |
  |---|---|
  | `bbs.pl` | 文章列表 |
  | `bbs.pl?act=click&file=<ID>` | 單篇文章和它的回應 |
  | `bbs.pl?srh=&keyword=&page=` | 搜尋和翻頁 |
  | `bbs.pl?act=post` | 發文表單 |
  | `bbs-admin.pl` | 管理登入（刪除文章、編輯頁面） |

- **文章 ID** 是發文時間去掉前導零後串起來的，例如 `2001416131018` 代表 2001/4/16 13:10:18。月和日沒有補零，所以 ID 本身有歧義，要以頁面上的「發表時間」為準。
- **列表欄位**：主題、作者、點閱數、回應數、發表時間、最後回應時間。
- **文章頁欄位**：文章主題、發表時間（`YYYY/M/D-HH:MM:SS`）、發表作者、發表內容，下面接回應，最後是回應表單（`username`、`subject`、`comments`）。
- **圖片幾乎都是外連**，不在 cgany 主機上，所以這次沒抓到。常見來源有 myweb.hinet.net、geocities.jp / geocities.co.jp、home.pchome.com.tw、groups.msn.com、hometown.aol.co.uk、photohighway.co.jp、home.kimo.com.tw。
- 板規（`/cg/rule.txt`）：每人每天最多 2 篇主題、每篇最多 5 張圖、禁止盜連。

### 2. vBulletin 2.2.x（itaiwan `/vbb/`，2001–2003）

- 現成的商業軟體，PHP＋MySQL。
- 存到的頁面以 `member.php`（1,055 頁，全是登入頁）和少量 `showthread.php`、`forumdisplay.php` 為主。
- phpMyAdmin 的 `tbl_properties.php` 頁面可以看到資料庫表格結構，`sql.php` 可以看到資料表內容。這些頁面已在 2026-10-23 補抓完成：設定類資料表完整，文章和會員只剩部分，筆數見 HANDOFF。

### 3. LeoBBS（itaiwan `/bbs/`，2001）

- Perl 論壇，大部分頁面都是 404，只剩少數列表頁。

### 4. phpBB 2.0.x ＋ Coppermine 1.3.2（bbs.cgany.com，約 2005）

- 都是開源軟體，舊版原始碼找得到。
- 存到的頁面有 `viewtopic.php` 約 1,450 頁，以及 Coppermine 的 `thumbnails.php`、`displayimage.php`。

### 5. www 入口（FrontPage 靜態頁）

- 框架式版面：`index.htm`、`main.htm`、`menu.htm`、`list.htm`、`menu.htc`。
- 另有 `cgr/`、`cr/`、`q7q7/`、`0z0z/` 等子目錄，也各放了一份 Perl 貼圖板。

## 還原的可行性

| 子系統 | 可行做法 |
|---|---|
| Perl 貼圖板 | 從 HTML 解析出文章、回應、作者、時間、圖片網址，用現代程式重寫一個行為相同的仿製版 |
| phpBB、Coppermine、vBulletin | 原汁原味版：用 Docker 架 PHP 4、MySQL 和同版本軟體，再把資料匯回去。輕量版：直接展示存檔的 HTML |
| 外連圖片 | 另外到 Wayback 查各圖床的存檔，命中率未知 |
| FrontPage 入口 | 存檔的靜態 HTML 改寫連結後就能直接用 |
