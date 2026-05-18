"""
SMBkits — Cold Email Mailer
Gemini API 개인화 생성 → Gmail SMTP 3계정 순환 발송
랜덤 워밍업 발송량 + 랜덤 제목/내용 + 랜덤 딜레이

Usage:
    python scrapers/mailer.py --week 1
    python scrapers/mailer.py --week 2 --dry-run   # 실제 발송 없이 테스트
"""

import os
import json
import time
import random
import smtplib
import gspread
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google import genai
from google.genai import types
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import argparse
import sys

load_dotenv("scrapers/.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SHEET_ID       = os.getenv("SHEET_ID")
SHEET_NAME     = os.getenv("SHEET_NAME")
CREDS_FILE     = os.getenv("CREDS_FILE")

MODEL = "gemini-3.1-flash-lite"

SMTP_ACCOUNTS = [
    {
        "name":  "James Harrison",
        "email": "jamessmbkits@gmail.com",
        "pw":    os.getenv("SMTP_JAMES_PW", "").replace(" ", ""),
    },
    {
        "name":  "Alex Bennett",
        "email": "alexsmbkits@gmail.com",
        "pw":    os.getenv("SMTP_ALEX_PW", "").replace(" ", ""),
    },
    {
        "name":  "Sarah Mitchell",
        "email": "sarahsmbkits@gmail.com",
        "pw":    os.getenv("SMTP_SARAH_PW", "").replace(" ", ""),
    },
]

# 워밍업 주차별 계정당 일일 발송 범위 (랜덤 상승/하락)
WARMUP = {
    1: (1, 4),
    2: (3, 7),
    3: (6, 12),
    4: (10, 20),
    5: (18, 30),
    6: (25, 35),
}

COL = {
    "business_name":   0,
    "city":            2,
    "country":         3,
    "website":         4,
    "email":           6,
    "google_rating":   9,
    "review_count":    10,
    "negative_review": 12,
    "sentiment_score": 13,
    "outreach_status": 14,
}

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def get_sheet():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)


def days_since(status: str) -> int:
    """'d0:2026-05-18' 형식에서 경과 일수 계산"""
    try:
        date_str = status.split(":")[1]
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (date.today() - d).days
    except Exception:
        return 0


def generate_email(lead: dict, sequence: str) -> dict | None:
    """Gemini로 개인화 이메일 생성 — 제목·내용 매번 다르게"""
    name    = lead.get("business_name", "")
    city    = lead.get("city", "")
    country = lead.get("country", "")
    rating  = lead.get("google_rating", "")
    reviews = lead.get("review_count", "")
    neg_rev = lead.get("negative_review", "")

    if sequence == "d0":
        neg_section = (
            f"Recent negative review snippet: \"{neg_rev[:200]}\""
            if neg_rev else "No negative review text available."
        )
        prompt = f"""You are writing a cold outreach email on behalf of SMBkits (smbkits.com),
a private AI reputation management tool for premium independent restaurants.

Target restaurant:
- Name: {name}
- Location: {city}, {country}
- Google Rating: {rating} stars ({reviews} reviews)
- {neg_section}

Write a SHORT, conversational cold email. Requirements:
1. Mention you ran a quick analysis of their Google reviews
2. Include the rating and review count naturally (1 sentence)
3. If negative review text is available, include a brief example AI-drafted response (2-3 sentences)
4. Mention smbkits.com — 7 AI tools for premium restaurants, starting at $19/month
5. End with a soft, no-pressure CTA

STRICT RULES:
- Subject: personal and curiosity-driven, NOT salesy. Never use: "partnership", "opportunity", "collaboration", "exciting"
- Body: under 150 words, plain text only, no bullet points, no bold
- Sound like a real human, not a marketer
- Every email must use different wording, structure, and opening — never repeat phrasing
- Sign off with just a first name

Respond ONLY in this exact JSON format (no markdown):
{{"subject": "...", "body": "..."}}"""

    elif sequence == "d3":
        prompt = f"""Write a very short follow-up cold email for {name} in {city}.

Context: You emailed them 3 days ago about their Google reviews and smbkits.com (AI reputation tool).
They haven't replied yet.

RULES:
- 2-3 sentences only
- Casual, human tone — like a real person checking in
- Reference the previous email naturally
- No pressure
- Different wording every time

Respond ONLY in JSON (no markdown):
{{"subject": "...", "body": "..."}}"""

    elif sequence == "d10":
        prompt = f"""Write a final short breakup-style cold email for {name} in {city}.

Context: Last follow-up. They have {reviews} Google reviews and a {rating} star rating.
You've emailed them twice already about smbkits.com.

RULES:
- 2-3 sentences only
- Mention one specific stat ({reviews} reviews OR {rating} stars)
- Mention smbkits.com once
- Friendly, no hard feelings — you're moving on
- Different wording every time

Respond ONLY in JSON (no markdown):
{{"subject": "...", "body": "..."}}"""

    else:
        return None

    try:
        response = gemini_client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=1.2,  # 높은 temperature → 다양한 문장 생성
            ),
        )
        result = json.loads(response.text)
        return {
            "subject": result.get("subject", ""),
            "body":    result.get("body", ""),
        }
    except Exception as e:
        print(f"  Gemini 생성 오류: {e}")
        return None


def send_email(account: dict, to_email: str, subject: str, body: str) -> bool:
    """Gmail SMTP SSL로 발송"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{account['name']} <{account['email']}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(account["email"], account["pw"])
            server.sendmail(account["email"], to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"  SMTP 오류 ({account['email']}): {e}")
        return False


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--week",    type=int,  default=1,     help="워밍업 주차 (1~6)")
    parser.add_argument("--dry-run", action="store_true",      help="실제 발송 없이 출력만")
    args = parser.parse_args()

    week   = max(1, min(6, args.week))
    lo, hi = WARMUP[week]
    today  = date.today().strftime("%Y-%m-%d")

    # 계정별 오늘 목표 건수 (랜덤)
    per_account = {acc["email"]: random.randint(lo, hi) for acc in SMTP_ACCOUNTS}
    total_target = sum(per_account.values())
    print(f"[Week {week}] 오늘 목표: {total_target}건 | {per_account}\n")
    if args.dry_run:
        print("*** DRY RUN 모드 — 실제 발송 없음 ***\n")

    sheet    = get_sheet()
    all_rows = sheet.get_all_values()
    rows     = all_rows[1:]

    # 시퀀스별 리드 분류
    d0_leads, d3_leads, d10_leads = [], [], []

    for i, row in enumerate(rows):
        email  = row[COL["email"]]          if len(row) > 6  else ""
        status = row[COL["outreach_status"]] if len(row) > 14 else ""
        if not email:
            continue

        if not status:
            d0_leads.append((i, row))
        elif status.startswith("d0:") and days_since(status) >= 3:
            d3_leads.append((i, row))
        elif status.startswith("d3:") and days_since(status) >= 7:
            d10_leads.append((i, row))

    print(f"D0(신규): {len(d0_leads)}건 | D+3 대기: {len(d3_leads)}건 | D+10 대기: {len(d10_leads)}건\n")

    # 발송 큐: d10 → d3 → d0 우선순위
    queue = (
        [(i, row, "d10") for i, row in d10_leads] +
        [(i, row, "d3")  for i, row in d3_leads]  +
        [(i, row, "d0")  for i, row in d0_leads]
    )

    sent_count = {acc["email"]: 0 for acc in SMTP_ACCOUNTS}
    total_sent = 0

    for i, row, sequence in queue:
        # 모든 계정 목표 달성 시 종료
        available = [
            acc for acc in SMTP_ACCOUNTS
            if sent_count[acc["email"]] < per_account[acc["email"]]
        ]
        if not available:
            break

        account  = random.choice(available)
        to_email = row[COL["email"]] if len(row) > 6 else ""
        if not to_email:
            continue

        lead = {
            "business_name":  row[COL["business_name"]]  if len(row) > 0  else "",
            "city":           row[COL["city"]]            if len(row) > 2  else "",
            "country":        row[COL["country"]]         if len(row) > 3  else "",
            "google_rating":  row[COL["google_rating"]]   if len(row) > 9  else "",
            "review_count":   row[COL["review_count"]]    if len(row) > 10 else "",
            "negative_review":row[COL["negative_review"]] if len(row) > 12 else "",
        }

        print(f"[{sequence.upper()}] {lead['business_name']} → {to_email}")
        print(f"  발송자: {account['name']} <{account['email']}>")

        content = generate_email(lead, sequence)
        if not content:
            continue

        print(f"  제목: {content['subject']}")
        print(f"  내용 미리보기: {content['body'][:80]}...")

        if not args.dry_run:
            success = send_email(account, to_email, content["subject"], content["body"])
        else:
            success = True  # dry-run은 항상 성공 처리

        if success:
            sent_count[account["email"]] += 1
            total_sent += 1
            new_status = f"{sequence}:{today}"

            if not args.dry_run:
                sheet.update_cell(i + 2, COL["outreach_status"] + 1, new_status)

            print(f"  ✅ {'[DRY]' if args.dry_run else ''} 완료 | 상태: {new_status}")
        else:
            print(f"  ❌ 실패")

        # 랜덤 딜레이 (인간 행동 모방) — dry-run은 스킵
        if not args.dry_run:
            delay = random.randint(60, 180)
            print(f"  ⏳ {delay}초 대기...\n")
            time.sleep(delay)
        else:
            print()

    print(f"\n=== 완료 | 총 {total_sent}건 발송 ===")
    for acc in SMTP_ACCOUNTS:
        print(f"  {acc['name']}: {sent_count[acc['email']]}건")


if __name__ == "__main__":
    main()
