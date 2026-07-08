<p align="center"><img src="static/logo.png" alt="RippleSearch" width="72" /></p>
<h1 align="center">RippleSearch</h1>
<p align="center"><b>Type what you sell and where. Get a clean CSV of local businesses to call.</b></p>
<p align="center">
  <code>◐ Working</code> &nbsp;·&nbsp; Flask · Playwright · Pandas
</p>

> Google already lists every business in a city. RippleSearch just reads that list for you and hands back a spreadsheet you can actually work.

Give it a search term and a location, watch it walk the Google local results page by page, and download the leads as a CSV. A live console streams every step as it happens, so you are never staring at a frozen screen wondering if it is working.

## Why it exists
Finding local leads by hand means opening result after result and copying names, addresses, and phone numbers into a sheet. It is slow, dull, and easy to fumble. RippleSearch turns that whole grind into one query and a download, so prospecting is minutes instead of an afternoon.

## How it works
```
Type query + location  ->  Walk Google local results  ->  Pull name, address, phone, rating  ->  Stream to console  ->  Download CSV
```
| Step | What happens |
|------|--------------|
| Enter a query | You type what you are looking for and the location (for example a trade and a state). |
| Scrape the results | A headless browser opens the Google local listings and pages through them, up to ten pages. |
| Extract the details | Each listing gives up its business name, address, phone number, and rating. |
| Watch it live | A command-style console streams progress and running totals over a live event stream. |
| Download | Results collect into a CSV you can export and open in any spreadsheet. |

## What you get
| Feature | What it does |
|---------|--------------|
| One-line search | A single query (term plus location) kicks off the whole run. |
| Multi-page crawl | Pages through the local results automatically so you are not capped at the first screen. |
| Clean lead fields | Name, address, phone (normalized), and rating per business. |
| Live console | A retro command console prints each step and lead count in real time. |
| CSV export | Download the collected leads, or grab the latest run on demand. |

## Under the hood
Flask serves the app and streams progress over Server-Sent Events. Playwright drives a headless Chromium through the Google local results, Pandas assembles the rows, and the whole thing exports to CSV.
