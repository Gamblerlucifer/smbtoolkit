"""
SMBkits — TripAdvisor Scraper
업체명 + 도시 → TripAdvisor 검색 → 상세 페이지 → 이메일/전화/웹사이트 추출
"""

import os
import sys
import re
import asyncio
import random
import gspread
from playwright.async_api import async_playwright
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv("scrapers/.env", override=True)

DAILY_LIMIT = 500

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_file(
    os.environ.get("CREDS_FILE", "scrapers/credentials.json"), scopes=SCOPES
)
gc    = gspread.authorize(creds)
sheet = gc.open_by_key(os.environ["SHEET_ID"]).worksheet(os.environ["SHEET_NAME"])

headers = sheet.row_values(1)

def ensure_col(name):
    if name not in headers:
        sheet.update_cell(1, len(headers) + 1, name)
        headers.append(name)

def col(name):
    return headers.index(name) + 1

ensure_col("phone")
ensure_col("scraper_done")

web_col     = col("website")
email_col   = col("email")
phone_col   = col("phone")
insta_col   = col("instagram")
rating_col  = col("google_rating")
reviews_col = col("review_count")
done_col    = col("scraper_done")

# scraper_done 없는 행만 타겟
all_records = sheet.get_all_records()
print(f"총 {len(all_records)}개 리드 탐색 중...")

targets = []
for i, rec in enumerate(all_records, start=2):
    if not rec.get("scraper_done"):
        targets.append({
            "row": i,
            "name": rec.get("business_name", ""),
            "city": rec.get("city", ""),
            "country": rec.get("country", ""),
        })
    if len(targets) >= DAILY_LIMIT:
        break

print(f"미처리: {len(targets)}개\n")

async def scrape_one(page, name, city):
    result = {"email": "", "website": "", "phone": "", "rating": None, "reviews": None}

    try:
        # TripAdvisor 검색
        query = f"{name} {city}".replace(" ", "%20")
        await page.goto(
            f"https://www.tripadvisor.com/Search?q={query}&searchSessionId=x&geo=1",
            wait_until="domcontentloaded", timeout=20000
        )
        await page.wait_for_timeout(random.randint(2000, 3500))

        # 첫 번째 레스토랑 결과 클릭
        result_link = await page.query_selector("a[href*='/Restaurant_Review']")
        if not result_link:
            return result

        href = await result_link.get_attribute("href")
        detail_url = "https://www.tripadvisor.com" + href if href.startswith("/") else href
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(random.randint(2000, 3000))

        html = await page.content()

        # 이메일 (mailto:)
        mailto = await page.query_selector("a[href^='mailto:']")
        if mailto:
            href = await mailto.get_attribute("href")
            result["email"] = href.replace("mailto:", "").split("?")[0].strip()

        # 웹사이트
        web_el = await page.query_selector("a[data-item-type='website'], a[href*='__sessionSig']:not([href*='tripadvisor'])")
        if not web_el:
            # data-automation="WebsiteLink" 패턴
            web_el = await page.query_selector("[data-automation='WebsiteLink']")
        if web_el:
            w = await web_el.get_attribute("href") or ""
            if w and "tripadvisor" not in w:
                result["website"] = w.split("?")[0]

        # 전화번호
        phone_el = await page.query_selector("a[href^='tel:']")
        if phone_el:
            result["phone"] = (await phone_el.get_attribute("href")).replace("tel:", "").strip()
        else:
            m = re.search(r"\+[\d\s\-().]{7,20}", html)
            if m:
                result["phone"] = m.group(0).strip()

        # 평점/리뷰수
        m = re.search(r'"aggregateRating".*?"ratingValue"\s*:\s*([\d.]+).*?"reviewCount"\s*:\s*(\d+)', html, re.DOTALL)
        if m:
            result["rating"]  = float(m.group(1))
            result["reviews"] = int(m.group(2))

    except Exception as e:
        print(f"    오류: {str(e)[:80]}")

    return result

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
        )
        page = await context.new_page()

        found = 0
        for rec in targets:
            row_num = rec["row"]
            name    = rec["name"]
            city    = rec["city"]
            print(f"[{row_num}] {name[:30]}")

            r = await scrape_one(page, name, city)

            updates = []
            if r["email"]:   updates.append((row_num, email_col,   r["email"]));   found += 1
            if r["website"]: updates.append((row_num, web_col,     r["website"]))
            if r["phone"]:   updates.append((row_num, phone_col,   r["phone"]))
            if r["rating"]:  updates.append((row_num, rating_col,  r["rating"]))
            if r["reviews"]: updates.append((row_num, reviews_col, r["reviews"]))
            updates.append((row_num, done_col, "Y"))

            sheet.batch_update([
                {"range": gspread.utils.rowcol_to_a1(rw, c), "values": [[v]]}
                for rw, c, v in updates
            ])

            print(f"  email:{r['email'] or '-'} | web:{r['website'][:35] or '-'} | tel:{r['phone'] or '-'}")
            await asyncio.sleep(random.uniform(3, 5))

        await browser.close()
    print(f"\n완료 — {found}/{len(targets)}개 이메일 수집")

if __name__ == "__main__":
    asyncio.run(main())
