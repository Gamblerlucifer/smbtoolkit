"""
SMBkits — Google Search Stealth Scraper
Places API 없이 구글 검색 지식 패널에서 rating + website 무료 추출

Usage:
    python scrapers/gmaps_scraper.py --chunk 0 --total-chunks 4 --limit 200
"""

import asyncio
import os
import re
import random
import requests
import gspread
from playwright.async_api import async_playwright
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

SOCIAL_EXCLUDE = ["instagram.com", "facebook.com", "twitter.com", "youtube.com",
                  "tripadvisor.com", "yelp.com", "google.com", "t.co",
                  "sevenrooms.com", "resy.com", "opentable.com", "inline.app",
                  "booking.com", "airbnb.com", "zomato.com", "tabelog.com"]

IMG_EXT   = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico")
SPAM_WORDS = ["example", "sentry", "pixel", "noreply", "no-reply", "wixpress",
              "schema", "wordpress", "jquery", "cloudflare", "analytics",
              "support@", "admin@", "postmaster@", "abuse@"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

def is_social(url):
    return any(s in url for s in SOCIAL_EXCLUDE) if url else False

def get_sheet():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

async def human_delay():
    """1.5 ~ 4.5초 인간형 랜덤 딜레이"""
    await asyncio.sleep(random.uniform(1.5, 4.5))

async def make_stealth_context(browser):
    """매 요청마다 랜덤 핑거프린트 컨텍스트 생성"""
    context = await browser.new_context(
        viewport={"width": random.randint(1200, 1920), "height": random.randint(700, 1080)},
        user_agent=random.choice(USER_AGENTS),
        locale="en-US",
        timezone_id=random.choice(["America/New_York", "America/Los_Angeles", "Europe/London"]),
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    page = await context.new_page()

    # webdriver 흔적 완전 마스킹
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        window.chrome = {runtime: {}};
        delete window.__playwright;
        delete window.__pw_manual;
    """)

    return context, page

async def search_google(page, name, city, country):
    """Google Search 지식 패널에서 rating + website 추출"""
    query = f"{name} {city} {country}"
    encoded = requests.utils.quote(query)
    url = f"https://www.google.com/search?q={encoded}&hl=en&gl=us"

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await human_delay()

        content = await page.content()

        # CAPTCHA 감지
        if "unusual traffic" in content or await page.query_selector("form#captcha-form, div#recaptcha"):
            print("  CAPTCHA 감지 - 스킵")
            return None

        rating       = ""
        review_count = ""
        website      = ""

        # ── Rating 추출 (다중 패턴 폴백) ──────────────────
        # 패턴 1: schema.org ratingValue
        m = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)"?', content)
        if m:
            rating = m.group(1)

        # 패턴 2: aria-label "Rated X.X out of 5"
        if not rating:
            m = re.search(r'Rated ([\d.]+) out of 5', content)
            if m:
                rating = m.group(1)

        # 패턴 3: 지식 패널 내 X.X 형태 (1.0~5.0 범위)
        if not rating:
            for m in re.finditer(r'\b([1-4]\.[0-9]|5\.0)\b', content):
                rating = m.group(1)
                break

        # ── Review count 추출 ─────────────────────────────
        m = re.search(r'([\d,]+)\s+(?:Google\s+)?reviews?', content, re.IGNORECASE)
        if m:
            review_count = m.group(1).replace(",", "")

        # ── Website 추출 ──────────────────────────────────
        # 지식 패널 공식 웹사이트 링크
        for sel in ['[data-attrid*="website"] a', '[data-attrid*="url"] a',
                    'a[jsname][href^="http"]:not([href*="google."])']:
            el = await page.query_selector(sel)
            if el:
                href = await el.get_attribute("href") or ""
                if href and not is_social(href) and "google." not in href:
                    website = href.split("&")[0]  # 추적 파라미터 제거
                    break

        return {
            "rating":       rating,
            "review_count": review_count,
            "website_uri":  website,
        }

    except Exception as e:
        print(f"  검색 오류: {e}")
        return None

def extract_email(url):
    """requests로 이메일 추출 (contact/about 페이지 포함)"""
    if not url or is_social(url):
        return ""
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    for target in [url, url.rstrip("/") + "/contact", url.rstrip("/") + "/about"]:
        try:
            res = requests.get(target, headers=headers, timeout=8)
            emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", res.text)
            filtered = []
            for e in emails:
                e_low = e.lower()
                if any(e_low.endswith(x) for x in IMG_EXT): continue
                if any(x in e_low for x in SPAM_WORDS): continue
                tld = e_low.rsplit(".", 1)[-1]
                if tld in {"png","jpg","jpeg","gif","svg","webp","ico"}: continue
                filtered.append(e)
            if filtered:
                return filtered[0]
        except:
            continue
    return ""

async def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk",        type=int, default=0,   help="청크 인덱스 (0-based)")
    parser.add_argument("--total-chunks", type=int, default=1,   help="전체 병렬 청크 수")
    parser.add_argument("--limit",        type=int, default=200, help="이번 실행에서 처리할 최대 행 수")
    args = parser.parse_args()

    sheet    = get_sheet()
    all_rows = sheet.get_all_values()
    rows     = all_rows[1:]

    # rating 없는 행만
    unprocessed = [(i, r) for i, r in enumerate(rows)
                   if not (len(r) > 9 and r[COL["google_rating"]])]

    # 이 청크가 담당할 행 (라운드로빈 분배 → 서로 다른 IP가 다른 나라 처리)
    my_rows = [x for j, x in enumerate(unprocessed) if j % args.total_chunks == args.chunk]
    my_rows = my_rows[:args.limit]

    total_unprocessed = len(unprocessed)
    print(f"[Chunk {args.chunk}/{args.total_chunks-1}] 미처리: {total_unprocessed}행 | 담당: {len(my_rows)}행")
    if not my_rows:
        print("처리할 행 없음 - 완료")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for idx, (i, row) in enumerate(my_rows):
            name    = row[COL["business_name"]] if len(row) > 0 else ""
            city    = row[COL["city"]]          if len(row) > 2 else ""
            country = row[COL["country"]]       if len(row) > 3 else ""

            if not name:
                continue

            print(f"  [{idx+1}/{len(my_rows)}] {name} - {city}, {country}")

            # 매 요청마다 새 컨텍스트 (핑거프린트 교체)
            context, page = await make_stealth_context(browser)
            try:
                result = await search_google(page, name, city, country)
            finally:
                await context.close()

            if not result:
                continue

            rating       = result["rating"]
            review_count = result["review_count"]
            website_uri  = result["website_uri"]

            full_row = list(row) + [""] * (17 - len(row))

            current_website = full_row[COL["website"]]
            if is_social(current_website):
                current_website = ""
            website = current_website or website_uri
            if is_social(website):
                website = ""

            email = full_row[COL["email"]]
            if website and not email:
                email = extract_email(website)

            sentiment = min(100, int(float(rating) * 20)) if rating else 50

            print(f"    rating: {rating or '-'} ({review_count}개) | "
                  f"website: {website or '없음'} | email: {email or '없음'}")

            row_num = i + 2
            full_row[COL["google_rating"]]   = rating
            full_row[COL["review_count"]]    = review_count
            full_row[COL["sentiment_score"]] = sentiment
            full_row[COL["website"]]         = website
            full_row[COL["email"]]           = email

            sheet.update(range_name=f"A{row_num}:Q{row_num}", values=[full_row])

        await browser.close()

    print(f"\n[Chunk {args.chunk}] 완료")

if __name__ == "__main__":
    asyncio.run(main())
