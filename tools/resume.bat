@echo off
rem Resume the Wayback crawl of cgany.com (all subdomains).
rem URLs already in index_a.tsv / index_b.tsv are skipped; failed ones are retried.
rem Close the windows at any time to pause; run this file again to continue.
rem The URL lists (tc_a.txt / tc_b.txt) and the archive stay on the local disk, outside this repo.
set LISTS=%USERPROFILE%\cgany_crawl
set ARC=%USERPROFILE%\cgany_com_archive
start "cgany crawl A" cmd /k python -I "%~dp0crawl2.py" "%LISTS%\tc_a.txt" "%ARC%" index_a.tsv
start "cgany crawl B" cmd /k python -I "%~dp0crawl2.py" "%LISTS%\tc_b.txt" "%ARC%" index_b.tsv
