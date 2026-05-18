"""
SMBkits — Async Multi-Engine Scraper
Google first → Bing fallback | async httpx | batch Sheets write | email 분리

Usage:
    python scrapers/gmaps_scraper.py --limit 500 --workers 3
    python scrapers/gmaps_scraper.py --email-only --limit 500   # email 추출만
"""

import asyncio
import httpx
import urllib.parse
import os
import re
import random
import time
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import argparse
import sys

load_dotenv("scrapers/.env")

SHEET_ID   = os.getenv("SHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")
CREDS_FILE = os.getenv("CREDS_FILE")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COL = {
    "business_name":  0,
    "city":           2,
    "country":        3,
    "website":        4,
    "email":          6,
    "google_rating":  9,
    "review_count":   10,
    "negative_review":12,
    "sentiment_score":13,
    "outreach_status":14,
}

BATCH_SIZE = 30   # 몇 건마다 Sheets에 일괄 저장

SOCIAL_EXCLUDE = ["instagram.com", "facebook.com", "twitter.com", "youtube.com",
                  "tripadvisor.com", "yelp.com", "google.com", "t.co",
                  "sevenrooms.com", "resy.com", "opentable.com", "inline.app",
                  "booking.com", "airbnb.com", "zomato.com", "tabelog.com"]

IMG_EXT    = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico")
SPAM_WORDS = ["example", "sentry", "pixel", "noreply", "no-reply", "wixpress",
              "schema", "wordpress", "jquery", "cloudflare", "analytics",
              "support@", "admin@", "postmaster@", "abuse@"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

def is_social(url: str) -> bool:
    return any(s in url for s in SOCIAL_EXCLUDE) if url else False

def get_sheet():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ── HTTP 클라이언트 팩토리 ─────────────────────────────────
def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={
            "User-Agent":                random.choice(USER_AGENTS),
            "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language":           "en-US,en;q=0.9",
            "Accept-Encoding":           "gzip, deflate, br",
            "DNT":                       "1",
            "Sec-Ch-Ua":                 '"Chromium";v="124", "Google Chrome";v="124"',
            "Sec-Ch-Ua-Mobile":          "?0",
            "Sec-Ch-Ua-Platform":        '"Windows"',
            "Sec-Fetch-Dest":            "document",
            "Sec-Fetch-Mode":            "navigate",
            "Sec-Fetch-Site":            "none",
        },
        timeout=15,
        follow_redirects=True,
    )

# ── Google Search 파싱 ───────────────────────────────────────
async def search_google(client: httpx.AsyncClient, name: str, city: str, country: str) -> dict | None:
    query   = f"{name} {city} {country}"
    encoded = urllib.parse.quote(query)
    url     = f"https://www.google.com/search?q={encoded}&hl=en&gl=us"

    try:
        r = await client.get(url)
        if r.status_code == 429 or r.status_code == 503:
            return None
        html = r.text
        if "unusual traffic" in html or len(html) < 5000:
            return None

        return _parse_rating_website(html)
    except Exception:
        return None

# ── Bing Search fallback ─────────────────────────────────────
async def search_bing(client: httpx.AsyncClient, name: str, city: str, country: str) -> dict | None:
    query   = f"{name} {city} {country} restaurant"
    encoded = urllib.parse.quote(query)
    url     = f"https://www.bing.com/search?q={encoded}&setlang=en-US&cc=US"

    try:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        html = r.text

        rating = review_count = website = ""

        # Bing knowledge panel rating (TripAdvisor/Yelp 통합)
        m = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)"?', html)
        if m:
            rating = m.group(1)

        m = re.search(r'([\d,]+)\s+reviews?', html, re.IGNORECASE)
        if m:
            review_count = m.group(1).replace(",", "")

        # Bing 공식 웹사이트 링크
        m = re.search(r'<a[^>]+href="(https?://(?!(?:www\.)?(?:bing|microsoft)\.)[^"]+)"[^>]*>\s*(?:Official Site|Website|Visit website)',
                      html, re.IGNORECASE)
        if m:
            candidate = m.group(1)
            if not is_social(candidate):
                website = candidate

        # fallback: 지식 패널 내 외부 링크
        if not website:
            for m in re.finditer(r'href="(https?://(?!(?:www\.)?(?:bing|microsoft|msn)\.)([^"]+))"', html):
                candidate = m.group(1)
                if not is_social(candidate) and "bing.com" not in candidate:
                    website = candidate
                    break

        if rating or website:
            return {"rating": rating, "review_count": review_count, "website_uri": website}
        return None

    except Exception:
        return None

# ── 공통 HTML 파싱 ──────────────────────────────────────────
def _parse_rating_website(html: str) -> dict:
    rating = review_count = website = ""

    m = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)"?', html)
    if m:
        rating = m.group(1)

    if not rating:
        m = re.search(r'Rated ([\d.]+) out of 5', html)
        if m:
            rating = m.group(1)

    m = re.search(r'([\d,]+)\s+(?:Google\s+)?reviews?', html, re.IGNORECASE)
    if m:
        review_count = m.group(1).replace(",", "")

    if not review_count:
        m = re.search(r'"reviewCount"\s*:\s*"?([\d]+)"?', html)
        if m:
            review_count = m.group(1)

    # 공식 웹사이트 링크
    for pat in [
        r'data-attrid="[^"]*(?:website|url)[^"]*"[^>]*href="([^"]+)"',
        r'"url"\s*:\s*"(https?://(?!(?:www\.)?google\.)[^"]+)"',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            candidate = m.group(1).split("&")[0]
            if not is_social(candidate) and "google." not in candidate:
                website = candidate
                break

    return {"rating": rating, "review_count": review_count, "website_uri": website}

# ── 이메일 추출 (async) ──────────────────────────────────────
async def extract_email_async(client: httpx.AsyncClient, url: str) -> str:
    if not url or is_social(url):
        return ""
    for target in [url, url.rstrip("/") + "/contact", url.rstrip("/") + "/about"]:
        try:
            r = await client.get(target, timeout=8)
            emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", r.text)
            filtered = []
            for e in emails:
                e_low = e.lower()
                if any(e_low.endswith(x) for x in IMG_EXT): continue
                if any(x in e_low for x in SPAM_WORDS): continue
                if e_low.rsplit(".", 1)[-1] in {"png","jpg","jpeg","gif","svg","webp","ico"}: continue
                filtered.append(e)
            if filtered:
                return filtered[0]
        except Exception:
            continue
    return ""

# ── 단일 행 처리 ─────────────────────────────────────────────
async def process_row(client: httpx.AsyncClient, i: int, row: list, idx: int, total: int) -> dict | None:
    name    = row[COL["business_name"]] if len(row) > 0 else ""
    city    = row[COL["city"]]          if len(row) > 2 else ""
    country = row[COL["country"]]       if len(row) > 3 else ""

    if not name:
        return None

    print(f"[{idx+1}/{total}] {name} - {city}, {country}")

    # Google → Bing fallback
    result = await search_google(client, name, city, country)
    source = "Google"
    if not result or (not result.get("rating") and not result.get("website_uri")):
        await asyncio.sleep(random.uniform(0.5, 1.5))
        result = await search_bing(client, name, city, country)
        source = "Bing"

    if not result:
        print(f"  결과 없음")
        return None

    rating       = result.get("rating", "")
    review_count = result.get("review_count", "")
    website_uri  = result.get("website_uri", "")

    full_row = list(row) + [""] * (17 - len(row))

    current_website = full_row[COL["website"]]
    if is_social(current_website):
        current_website = ""
    website = current_website or website_uri
    if is_social(website):
        website = ""

    # 이메일 추출
    email = full_row[COL["email"]]
    if website and not email:
        email = await extract_email_async(client, website)

    sentiment = min(100, int(float(rating) * 20)) if rating else 50

    print(f"  [{source}] rating: {rating or '-'} ({review_count}개) | "
          f"website: {website or '없음'} | email: {email or '없음'}")

    full_row[COL["google_rating"]]   = rating
    full_row[COL["review_count"]]    = review_count
    full_row[COL["sentiment_score"]] = sentiment
    full_row[COL["website"]]         = website
    full_row[COL["email"]]           = email

    return {"row_num": i + 2, "full_row": full_row}

# ── 배치 Sheets 저장 ─────────────────────────────────────────
def batch_write(sheet, pending: list):
    if not pending:
        return
    data = [{"range": f"A{p['row_num']}:Q{p['row_num']}", "values": [p["full_row"]]} for p in pending]
    sheet.batch_update(data)
    print(f"  [Sheets] {len(pending)}행 일괄 저장 완료")

# ── email-only 모드 (website 있고 email 없는 행만) ───────────
async def email_only_mode(sheet, rows: list, limit: int, workers: int):
    targets = [(i, r) for i, r in enumerate(rows)
               if (len(r) > 4 and r[COL["website"]] and not is_social(r[COL["website"]]))
               and not (len(r) > 6 and r[COL["email"]])][:limit]

    print(f"[email-only] 대상: {len(targets)}행")

    sem     = asyncio.Semaphore(workers)
    pending = []

    async def worker(i, row):
        async with sem:
            full_row = list(row) + [""] * (17 - len(row))
            async with make_client() as client:
                email = await extract_email_async(client, full_row[COL["website"]])
            if email:
                full_row[COL["email"]] = email
                print(f"  email: {email} ← {full_row[COL['website']][:40]}")
                pending.append({"row_num": i + 2, "full_row": full_row})
                if len(pending) >= BATCH_SIZE:
                    batch_write(sheet, pending[:])
                    pending.clear()
            await asyncio.sleep(random.uniform(0.3, 1.0))

    await asyncio.gather(*[worker(i, r) for i, r in targets])
    batch_write(sheet, pending)

# ── 메인 ─────────────────────────────────────────────────────
async def main_async(args):
    sheet    = get_sheet()
    all_rows = sheet.get_all_values()
    rows     = all_rows[1:]

    if args.email_only:
        await email_only_mode(sheet, rows, args.limit, args.workers)
        return

    unprocessed = [(i, r) for i, r in enumerate(rows)
                   if not (len(r) > 9 and r[COL["google_rating"]])]

    my_rows = [x for j, x in enumerate(unprocessed) if j % args.total_chunks == args.chunk]
    my_rows = my_rows[:args.limit]

    print(f"미처리 전체: {len(unprocessed)}행 | 이번 실행: {len(my_rows)}행 | workers: {args.workers}\n")
    if not my_rows:
        print("처리할 행 없음")
        return

    sem     = asyncio.Semaphore(args.workers)
    pending = []

    async def worker(idx, i, row):
        async with sem:
            await asyncio.sleep(random.uniform(0.5, 2.0) * idx % args.workers)  # 스타트 분산
            async with make_client() as client:
                result = await process_row(client, i, row, idx, len(my_rows))
            if result:
                pending.append(result)
            if len(pending) >= BATCH_SIZE:
                batch_write(sheet, pending[:])
                pending.clear()

    await asyncio.gather(*[worker(idx, i, row) for idx, (i, row) in enumerate(my_rows)])
    batch_write(sheet, pending)  # 나머지 flush
    print(f"\n완료")

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk",        type=int,  default=0,     help="청크 인덱스")
    parser.add_argument("--total-chunks", type=int,  default=1,     help="전체 청크 수")
    parser.add_argument("--limit",        type=int,  default=200,   help="처리할 최대 행 수")
    parser.add_argument("--workers",      type=int,  default=3,     help="동시 실행 worker 수")
    parser.add_argument("--email-only",   action="store_true",      help="email 추출만 실행")
    args = parser.parse_args()

    asyncio.run(main_async(args))

if __name__ == "__main__":
    main()
