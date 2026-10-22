# cgany 模擬復活計畫

用 Internet Archive（Wayback Machine）的存檔，在本機重建已關站的台灣早期 CG 論壇 cgany（2001–2011），讓它能像當年一樣離線瀏覽。

## 資料（不放在這個 repo）

抓下來的頁面只留在本機，不會進版控：

| 來源 | 頁數 | 本機位置 |
|---|---|---|
| cgany.itaiwan.net（2001–2003） | 799 | `C:\Users\Michael\cgany_archive\` |
| cgany.com 全部子網域（2003–2011 為主） | 23,457 / 23,768 | `C:\Users\Michael\cgany_com_archive\` |
| 網址清單、Wayback CDX 索引、抓不到的 311 頁清單 | — | `C:\Users\Michael\cgany_crawl\` |

- 頁面是 Big5 原始檔，存在 `raw\<子網域>\...`，對照表是 `index*.tsv`（原始網址、存檔時間、本機檔案、Wayback 網址）。
- 抓不到的 311 頁在 Wayback 上一律回 404，幾乎都是 2010–2011 年的留言板文章。

## 工具

| 檔案 | 說明 |
|---|---|
| `tools/crawl2.py` | 從 Wayback 下載清單裡的頁面，可中斷續跑：`python -I crawl2.py <清單> <輸出資料夾> <索引檔名>` |
| `tools/resume.bat` | 用兩個程序續跑 cgany.com 的下載 |

## 待辦

- [ ] 把 Big5 轉成 UTF-8
- [ ] 改寫頁面裡的連結，指向本機檔案（`bbs.pl?act=click&file=...` 這類 CGI 網址要對應到存檔檔名）
- [ ] 做一個本機伺服器或靜態網站，能從首頁一路點進各板和文章
- [ ] 整理各板的文章列表與索引頁（Wayback 沒存到的列表頁用已抓到的文章重建）
- [ ] 標示抓不到的頁面，避免點了是空白
