"""
SMBkits — Rating/Website 빠른 보완 스크립트
rating 없는 행만 Places API 호출 (Playwright 없음 → 빠름)

Usage:
    python scrapers/fix_rating.py
"""

import os
import time
import requests
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv("scrapers/.env")

SHEET_ID       = os.getenv("SHEET_ID")
SHEET_NAME     = os.getenv("SHEET_NAME")
CREDS_FILE     = os.getenv("CREDS_FILE")
PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COL = {
    "business_name":  0,
    "city":           2,
    "country":        3,
    "website":        4,
    "google_rating":  9,
    "review_count":   10,
    "negative_review":12,
    "sentiment_score":13,
    "outreach_status":14,
}

def get_sheet():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

def fetch_places(name, city, country):
    query = f"{name} {city} {country}".strip()
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": PLACES_API_KEY,
        "X-Goog-FieldMask": "places.rating,places.userRatingCount,places.reviews,places.websiteUri",
    }
    body = {"textQuery": query, "languageCode": "en"}
    try:
        res = requests.post(url, headers=headers, json=body, timeout=10)
        places = res.json().get("places", [])
        if not places:
            return None
        p = places[0]
        reviews  = p.get("reviews", [])
        negative = [r.get("text", {}).get("text", "") for r in reviews if r.get("rating", 5) <= 2]
        return {
            "rating":      p.get("rating", ""),
            "review_count":p.get("userRatingCount", ""),
            "negative":    negative[0][:300] if negative else "",
            "website_uri": p.get("websiteUri", ""),
        }
    except Exception as e:
        print(f"  Places API 오류: {e}")
        return None

def analyze_sentiment(negative_review, rating):
    if not negative_review:
        return min(100, int(float(rating) * 20)) if rating else 50
    negative_words = ["rude", "slow", "cold", "dirty", "bad", "terrible",
                      "awful", "horrible", "worst", "disappointed", "never again"]
    count = sum(1 for w in negative_words if w in negative_review.lower())
    base = min(100, int(float(rating) * 20)) if rating else 50
    return max(0, base - count * 5)

def main():
    sheet = get_sheet()
    all_rows = sheet.get_all_values()
    rows = all_rows[1:]

    # rating 없는 행만 필터
    targets = [(i, r) for i, r in enumerate(rows)
               if not (len(r) > 9 and r[COL["google_rating"]])]

    print(f"Rating 없는 행: {len(targets)}개 / 전체 {len(rows)}개")
    print(f"예상 소요: 약 {len(targets) * 0.6 / 60:.0f}분\n")

    for idx, (i, row) in enumerate(targets):
        name    = row[COL["business_name"]] if len(row) > 0 else ""
        city    = row[COL["city"]]    if len(row) > 2 else ""
        country = row[COL["country"]] if len(row) > 3 else ""

        if not name:
            continue

        print(f"[{idx+1}/{len(targets)}] {name} - {city}, {country}")

        places = fetch_places(name, city, country)
        if not places:
            print(f"  Places: 없음")
            time.sleep(0.3)
            continue

        rating       = places["rating"]
        review_count = places["review_count"]
        negative     = places["negative"]
        website_uri  = places["website_uri"]
        sentiment    = analyze_sentiment(negative, rating)

        print(f"  rating: {rating} ({review_count}개) | website: {website_uri or '없음'}")

        row_num = i + 2  # 1-based + header
        full_row = list(row) + [""] * (17 - len(row))

        full_row[COL["google_rating"]]   = rating
        full_row[COL["review_count"]]    = review_count
        full_row[COL["negative_review"]] = negative
        full_row[COL["sentiment_score"]] = sentiment
        # website 보완 (비어있을 때만)
        if not full_row[COL["website"]] and website_uri:
            full_row[COL["website"]] = website_uri

        sheet.update(range_name=f"A{row_num}:Q{row_num}", values=[full_row])
        time.sleep(0.5)

    print(f"\n완료 — rating 보완 완료")

if __name__ == "__main__":
    main()
