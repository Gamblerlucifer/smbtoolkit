# SMBKits — 마스터플랜 & 실행 체크리스트 v6.0
> 작성일: 2026-05-16 | 상태: 랜딩 페이지 제작 중
> v6.0: 마스터플랜 + Todo 통합 · 투웨이 전략 명확화

---

## 현재 진행 상황

```
✓ Next.js 프로젝트 생성 (C:\Users\jjun1\Desktop\Project\smbkits)
✓ GitHub 연결 (github.com/Gamblerlucifer/smbkits)
✓ Vercel 배포 (smbkits.vercel.app · 팀: MJM)
✓ 도메인 구매 (smbkits.com · Namecheap → Vercel DNS 연결)
✓ 투웨이 전략 확정

→ 지금: Way 2 프리미엄 랜딩 페이지 제작 중
```

---

## 투웨이 전략

> 같은 7개 도구, 완전히 다른 두 개의 시장 진입

|  | Way 2 — 프리미엄 (지금) | Way 1 — 커피슬로건 (나중) |
|--|----------------------|------------------------|
| **타겟** | 미슐랭·Forbes·SCA 등 인증 프리미엄 업장 | 전 세계 전 업종 일반 소상공인 |
| **가격** | $24.99 / $49.99 / $99.99/월 | $4.99/월 |
| **랜딩** | 프라이빗 브랜드 인프라 포지셔닝 | "오늘 커피값이 한 달 플랜입니다" |
| **슬로건** | Reputation, once damaged, rarely recovers. | You paid $5 for your morning coffee. That's our monthly plan. |
| **콜드메일** | 인증기관별 전용 스크래퍼 (직접 파싱) | Outscraper (Google Maps 전 업종) |
| **7개 도구** | 동일 | 동일 |

---

## 7개 AI 도구

| # | 도구명 (UI 표시) | 내부 코드명 | 기능 | 가격 |
|---|----------------|-----------|------|------|
| 1 | **Reputation Response** | Review Reply AI | 리뷰 감정 분석 → 등급별 처리 | $19/월 |
| 2 | **Social Presence** | Social Caption AI | 사진·메뉴 → SNS 캡션 생성 | $15/월 |
| 3 | **Local Positioning** | Competitor Intel | 경쟁 업체 리뷰 분석 리포트 | $29/월 |
| 4 | **Reputation Recovery** | Review Booster | 만족 고객 → 리뷰 요청 자동화 | $19/월 |
| 5 | **Brand Voice Library** | Menu Description AI | 메뉴·서비스 설명 문구 생성 | $9 일회성 |
| 6 | **Visibility Intelligence** | Local SEO Checker | Google 검색 노출 진단 | $29/월 |
| 7 | **Brand Responses** | Staff Reply Templates | 고객 불만 대응 스크립트 | $12/월 |

### Reputation Response — 핵심 로직

```
리뷰 수신 → Claude API 감정 분석 (1~5단계)
  ├── 4~5단계 (긍정) → 브랜드 톤 응답 자동 발행
  ├── 3단계 (중립)  → 초안 생성 → 오너 승인 후 발행
  └── 1~2단계 (부정) → 오너 즉시 알림 → 직접 대응
                       (AI 초안 참고용만 · 강제 발행 없음)
```

---

## 가격 구조

**Way 2 — 프리미엄**

| 등급 | 월간 | 연간 | 타겟 |
|------|------|------|------|
| Premium | $24.99 | $249.99 | 미슐랭 1스타 · Bib Gourmand |
| Elite | $49.99 | $499.99 | 2스타 · World's 50 Best |
| Prestige | $99.99 | $999.99 | 3스타 · 최고 등급 |

**Way 1 — 커피슬로건**

| 플랜 | 월간 | 연간 |
|------|------|------|
| Free | $0 | — |
| Standard | $4.99 | $49.99 |
| Plus | $9.99 | $99.99 |

---

## Phase 0 — 랜딩 페이지 (지금)

### Way 2 프리미엄 랜딩 (`app/page.tsx`)
- [x] 헤드라인 · 히어로 섹션
- [x] 인증기관 마키 (미슐랭·World's 50 Best·Forbes·SCA·Decanter·Tabelog)
- [x] 핵심 가치 스테이트먼트
- [x] Reputation Response 흐름 설명
- [x] 7개 도구 리스트
- [x] 프라이빗 액세스 신청 폼
- [ ] GitHub push → Vercel 자동 배포 확인
- [ ] www.smbkits.com DNS 정상 접속 확인

### 각 도구 상세 페이지 (7개)
- [ ] app/reputation-response/page.tsx
- [ ] app/social-presence/page.tsx
- [ ] app/local-positioning/page.tsx
- [ ] app/reputation-recovery/page.tsx
- [ ] app/brand-voice/page.tsx
- [ ] app/visibility-intelligence/page.tsx
- [ ] app/brand-responses/page.tsx

### Way 1 커피슬로건 랜딩 (Way 2 완성 후)
- [ ] app/smb/page.tsx (별도 랜딩)

---

## Phase 1 — 리드 DB 구축

### Google Sheets DB 설계
- [ ] Google Sheets 생성
- [ ] 컬럼 구조 세팅
  ```
  업장명 | 업종 | 도시 | 국가 | 웹사이트 | 이메일
  인증등급 | 리뷰수 | 최근부정리뷰 | 감정분석결과
  발송상태 | 답장여부 | 피드백
  ```
- [ ] 중복 제거 기준: 업장명 + 도시 조합

### Way 2 스크래퍼 (인증기관 직접 파싱 · GitHub Actions)

크롤링 쉬운 것 (우선):
- [ ] 미슐랭 레스토랑 — guide.michelin.com (GitHub 레포 존재)
- [ ] World's 50 Best Restaurants — theworlds50best.com
- [ ] World's 50 Best Bars — theworlds50best.com
- [ ] Forbes 5-Star Spa — forbestravelguide.com
- [ ] SCA 인증 카페 — sca.coffee
- [ ] 타베로그 고득점 — tabelog.com
- [ ] Decanter 95점+ — decanter.com

크롤링 어렵지만 포함:
- [ ] 반려동물 호텔·미용 — 커뮤니티 리스트 수동 수집

제외: 호텔 (전담 직원 + 중계 플랫폼)

- [ ] 중복 제거 + 인증 등급 컬럼 병합

### Way 1 스크래퍼 (Outscraper · GitHub Actions)
- [ ] Google Maps 전 업종 · 전 세계 주요 도시
- [ ] 도시별 배치 실행 (방콕 → 런던 → 두바이 → 뉴욕...)
- [ ] CSV → Google Sheets 자동 저장

### 이메일 추출
- [ ] Hunter.io 가입 (무료 25건/월)
- [ ] 각 업장 웹사이트 → Hunter.io → 이메일 추출
- [ ] NeverBounce 검증 (무료 1,000건)

### 리뷰 감정 분석 (콜드 이메일 개인화)
- [ ] Google Places API → 최근 리뷰 수집
- [ ] Claude API → 감정 분석 (1~5단계)
- [ ] 부정 리뷰 1개 추출 → 응답 초안 생성
- [ ] Sheets 업데이트

---

## Phase 2 — 콜드 이메일 파이프라인

### 발송 준비
- [ ] Gmail 발송 전용 계정 3개 생성
- [ ] Mailgun 가입 (무료 5,000건/월)
- [ ] Brevo 가입 (무료 300건/일)
- [ ] SPF / DKIM / DMARC 설정
- [ ] Gemini API 키 확보
- [ ] Instantly.ai 가입 + 워밍업 시작

**워밍업 스케줄:**
```
Week 1~2:  하루 5건
Week 3~4:  하루 10건
Week 5~6:  하루 20건
Week 7+:   하루 30건/계정 (3개 계정 → 최대 90건/일)
```

### Way 2 발송 (1차: 미슐랭 50개)
- [ ] 미슐랭 1스타 이상 50개 선정 (영어 리뷰 있음·웹사이트 있음·이메일 확보)
- [ ] 하루 25건씩 발송
- [ ] 답장 모니터링 + 수동 대응

---

## Phase 3 — 수요 검증

**기준: 관심 표현 5명 이상 → Phase 4 개발 착수**

- [ ] 어떤 업종이 답장률 높은지 기록
- [ ] 어떤 도구에 관심 보이는지 기록

### 피드백 수집 로그

| 날짜 | 업장명 | 인증등급 | 관심도구 | 피드백 |
|------|--------|---------|---------|--------|
|      |        |         |         |        |

---

## Phase 4 — 개발 (수요 검증 완료 후)

### 인프라 세팅
- [ ] Supabase 프로젝트 생성
- [ ] Stripe 계정 생성
- [ ] Anthropic API 키 발급

### 개발 순서 (Claude Code — 7개 동시 MVP)

```
Day 1~5:   Reputation Response (핵심 인프라)
             Google OAuth · 리뷰 수집 · 감정 분석 · Stripe

Day 6~8:   Social Presence + Brand Voice Library

Day 9~11:  Local Positioning + Reputation Recovery

Day 12~14: Visibility Intelligence + Brand Responses
```

**공통 인프라 (Day 1~5 완성 후 전부 재사용):**
- Google OAuth + Places API
- Claude Haiku API 호출 패턴
- Stripe 결제 (플랜별)
- Supabase 멀티 테넌트 DB
- Resend 이메일 알림

### 배포
- [ ] 7개 도구 페이지 전부 작동 확인
- [ ] Stripe 결제 테스트
- [ ] Google Search Console 등록 + Sitemap 제출

---

## Phase 5 — 스케일업 (MRR $500+ 달성 후)

- [ ] Way 1 커피슬로건 랜딩 제작
- [ ] Outscraper 파이프라인 가동 (전 업종 대량 발송)
- [ ] 발송 전용 도메인 추가 구매 + 워밍업
- [ ] 하루 50건 → 100건 확대
- [ ] Product Hunt 런칭 준비
- [ ] Build in Public (X/트위터)
- [ ] Reddit 커뮤니티 참여 (r/restaurantowners, r/smallbusiness)

---

## 참고: 이메일 시퀀스

### Day 0 — 레스토랑 타겟

**Subject:** Your [Restaurant Name] reviews — I ran an analysis

```
Hi [Owner name],

I ran a quick analysis of [Restaurant Name]'s recent Google reviews.

Here's what I found:

  5★ reviews (positive):  [N]개 → 자동 응답 가능
  3★ reviews (neutral):   [N]개 → 가볍게 응답 필요
  1~2★ reviews (negative): [N]개 → 직접 대응 필요

The [N] negative reviews are the ones that cost you customers.

Here's a draft response for the most recent one:

"[실제 부정 리뷰 원문 요약]"

---
"Thank you for taking the time to share your experience at
[Restaurant Name]. We're truly sorry we didn't meet your
expectations. This is not the standard we hold ourselves to,
and we'd love to make it right. Please reach out to us directly
at [이메일] — we'd like to take care of you personally."
---

Feel free to use it.

I built a tool that does this automatically — positive reviews
get a brand-standard response published immediately. Negative
reviews come straight to your phone. You respond personally.
Your brand stays yours.

smbkits.com — 7 AI tools for independent premium businesses.

✓ Reputation Response (sentiment triage 1~5)  → $19/월
✓ Social Presence (photo → caption)           → $15/월
✓ Local Positioning (competitor review intel)  → $29/월
✓ Reputation Recovery (auto review requests)  → $19/월
✓ Brand Voice Library (menu descriptions)     → $9 one-time
✓ Visibility Intelligence (Google SEO check)  → $29/월
✓ Brand Responses (complaint scripts)         → $12/월

Start with any one. Cancel anytime.

— [이름]
```

### Day 3 — 팔로업

**Subject:** The negative review — did you respond?

```
Hey [Owner name],

Just checking if the draft I sent was useful.

Most owners say the same: "I don't mind good reviews —
I just don't know how to handle bad ones without making it worse."

That's exactly what the triage system handles.

— [이름]
```

### Day 10 — 마지막

**Subject:** Last note — [Restaurant Name]

```
Hi [Owner name],

Restaurants that respond to reviews within 24 hours see
12% more foot traffic. [Restaurant Name] has [X] unanswered reviews.

smbkits.com — 7 AI tools, starting at $9. Try one, cancel anytime.

— [이름]
```

---

## 참고: API 비용

| 모델 | 입력 | 출력 | 용도 |
|------|------|------|------|
| **Claude Haiku 4.5** | $1/MTok | $5/MTok | 리뷰 응답 생성 — 기본 |
| Claude Sonnet 4.6 | $3/MTok | $15/MTok | 복잡한 분석 (필요 시) |

**리뷰 응답 1건당 비용:** ~$0.00044 (0.044센트)

> API 비용은 사실상 무시. 진짜 비용은 Stripe 수수료 (2.9%+$0.30/건).

---

## 참고: 자동화 스택

| 도구 | 역할 | 월 비용 |
|------|------|---------|
| Outscraper | Way 1 리드 스크래핑 | $0~5 |
| Hunter.io | 이메일 추출 | $0~49 |
| NeverBounce | 이메일 검증 | $0~8 |
| Instantly.ai | 시퀀스 발송 + 워밍업 | $37 |
| Mailgun / Brevo | 멀티 SMTP | $0 |
| Claude API | 개인화 초안 생성 | $3~10 |
| Vercel | 호스팅 | $0 |
| Supabase | DB | $0 |
| Stripe | 결제 (수익 발생 후 수수료만) | $0 |

---

## 참고: 리스크 대응

| 리스크 | 대응 |
|--------|------|
| 구글이 AI 응답 무료 내장 | 에이전트(자동 발행+모니터링)로 진화. 업종별 데이터 해자 |
| Claude API 비용 인상 | 마진 99.95% → 99.9%. 사실상 무관 |
| 콜드 이메일 스팸 필터 | 발송 도메인 분리 · SPF/DKIM/DMARC · 하루 30건/계정 초과 금지 |
| 경쟁사 진입 | 6개월 이내 선점. 리뷰 데이터 1만 건 이상이 해자 |

**종료 기준 (Kill Criteria):**
- Month 3: 400건 발송 후 유료 10명 미달 → 타겟/도구 재검토
- Month 6: MRR $500 미달 → 전면 피벗 검토

---

## 수익 현황

| 날짜 | 이벤트 | MRR |
|------|--------|-----|
| 2026-05-16 | 프로젝트 시작 | $0 |

---

*구 파일: SMBKits_마스터플랜_v5.md · SMBKits_Todo.md → 이 파일로 통합*
