"""
SMBkits — One-Shot Gemini Scraper
gemini-2.5-flash + Search Grounding (1,500 RPD 무료)
website / email / phone / instagram / google_rating 한 번에 추출
"""

import os
import sys
import re
import json
import time
import requests
import gspread
from google import genai
from google.genai import types
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv("scrapers/.env", override=True)

DAILY_LIMIT = 1490
RPM_DELAY   = 5.0
MODEL       = "gemini-2.5-flash"

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds  = Credentials.from_service_account_file(
    os.environ.get("CREDS_FILE", "scrapers/credentials.json"), scopes=SCOPES
)
gc     = gspread.authorize(creds)
sheet  = gc.open_by_key(os.environ["SHEET_ID"]).worksheet(os.environ["SHEET_NAME"])
gemini = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

headers = sheet.row_values(1)

def col(name):
    return headers.index(name) + 1

web_col     = col("website")
insta_col   = col("instagram")
email_col   = col("email")
rating_col  = col("google_rating")
reviews_col = col("review_count")

if "phone" not in headers:
    sheet.update_cell(1, len(headers) + 1, "phone")
    headers.append("phone")
phone_col = col("phone")

all_records = sheet.get_all_records()
print(f"총 {len(all_records)}개 리드 탐색 중...")

targets = []
for i, rec in enumerate(all_records, start=2):
    if not rec.get("email") or not rec.get("website"):
        targets.append((
            i,
            rec.get("business_name", ""),
            rec.get("city", ""),
            rec.get("country", ""),
        ))
    if len(targets) >= DAILY_LIMIT:
        break

print(f"오늘 처리: {len(targets)}개 / 한도 {DAILY_LIMIT}\n")

PROMPT = """Search Google for '{name}' restaurant in {city}, {country}.
Extract and return ONLY a JSON object:

```json
{{
  "website": "official website URL or null",
  "email": "contact email or null",
  "phone": "phone with country code or null",
  "instagram": "instagram URL or null",
  "google_rating": 4.5,
  "review_count": 1234
}}
```

Rules:
- website: official site ONLY, not tripadvisor/yelp/google/instagram/facebook/michelin
- email: real contact email only, not noreply/support/admin
- phone: include country code
- google_rating: Google Maps float or null
- review_count: integer or null"""

IMG_EXT    = (".png",".jpg",".jpeg",".gif",".svg",".webp",".ico")
SPAM_WORDS = ["noreply","no-reply","example","sentry","wixpress",
              "wordpress","cloudflare","support@","admin@","postmaster@"]
SOCIAL_EXCLUDE = ["instagram.com","facebook.com","twitter.com","tripadvisor.com",
                  "yelp.com","google.com","michelin.com","booking.com"]

def clean_instagram(val):
    """URL → @handle 변환"""
    if not val:
        return ""
    m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", val)
    if m:
        return "@" + m.group(1).rstrip("/")
    if val.startswith("@"):
        return val
    return ""

def crawl_email(url):
    """website 크롤링으로 email 추출"""
    if not url or any(s in url for s in SOCIAL_EXCLUDE):
        return ""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for target in [url, url.rstrip("/") + "/contact", url.rstrip("/") + "/about"]:
        try:
            res = requests.get(target, headers=headers, timeout=8)
            emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", res.text)
            for e in emails:
                el = e.lower()
                if any(el.endswith(x) for x in IMG_EXT): continue
                if any(x in el for x in SPAM_WORDS): continue
                return e
        except Exception:
            continue
    return ""

def parse_json(text):
    # ```json ... ``` 블록 추출
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # 백틱 없이 JSON만 있는 경우
    m = re.search(r"(\{.*?\})", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    return {}

for row_num, name, city, country in targets:
    print(f"[{row_num}] {name} ({city}, {country})")
    try:
        resp = gemini.models.generate_content(
            model=MODEL,
            contents=PROMPT.format(name=name, city=city, country=country),
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
            ),
        )
        result = parse_json(resp.text)

        website   = result.get("website") or ""
        email     = result.get("email") or ""
        instagram = clean_instagram(result.get("instagram") or "")
        phone     = result.get("phone") or ""

        # email 없으면 website 크롤링
        if website and not email:
            email = crawl_email(website)

        updates = []
        if website:                    updates.append((row_num, web_col,     website))
        if email:                      updates.append((row_num, email_col,   email))
        if phone:                      updates.append((row_num, phone_col,   phone))
        if instagram:                  updates.append((row_num, insta_col,   instagram))
        if result.get("google_rating"):updates.append((row_num, rating_col,  result["google_rating"]))
        if result.get("review_count"): updates.append((row_num, reviews_col, result["review_count"]))

        if updates:
            sheet.batch_update([
                {"range": gspread.utils.rowcol_to_a1(r, c), "values": [[v]]}
                for r, c, v in updates
            ])

        print(f"  web:{website or '-'} | email:{email or '-'} | ig:{instagram or '-'} | tel:{phone or '-'}")

    except Exception as e:
        print(f"  FAIL: {str(e)[:120]}")

    time.sleep(RPM_DELAY)

print("\n완료")
