import os
import re
import json
import math
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai

# =====================================================
# 기본 설정
# =====================================================

load_dotenv()

def get_secret(key, default=""):
    try:
        return os.getenv(key) or st.secrets.get(key, default)
    except Exception:
        return os.getenv(key) or default

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
DOMEME_API_KEY = get_secret("DOMEME_API_KEY")
DOMEME_SEARCH_URL = get_secret("DOMEME_SEARCH_URL")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(
    page_title="월천셀러 AI MD 상품발굴기",
    layout="wide"
)

# =====================================================
# 플랫폼별 MD 기준
# =====================================================

PLATFORM_RULES = {
    "스마트스토어": {
        "fee": 0.075,
        "min_price": 7900,
        "target_margin_rate": 0.25,
        "md_standard": """
스마트스토어 MD 기준:
- 네이버 쇼핑 검색형 상품명 중요
- 생활불편 해결형 상품 선호
- 리뷰 쌓기 쉬운 저가~중가 상품 유리
- 상표권, 브랜드명, 과장광고, 의료효능 표현 위험
- 썸네일 개선으로 클릭률을 올릴 수 있는 상품 가산점
"""
    },
    "옥션/지마켓": {
        "fee": 0.13,
        "min_price": 8900,
        "target_margin_rate": 0.28,
        "md_standard": """
옥션/지마켓 MD 기준:
- 가격 경쟁력과 무료배송 구조 중요
- 직관적인 상품명 중요
- 생활용품, 계절상품, 차량용품, 잡화류 적합
- 옵션 복잡한 상품 감점
- CS 적고 반복 판매 가능한 상품 가산점
"""
    },
    "토스쇼핑": {
        "fee": 0.11,
        "min_price": 8900,
        "target_margin_rate": 0.30,
        "md_standard": """
토스쇼핑 MD 기준:
- 충동구매 가능성 중요
- 8,900원~19,900원 가격대 유리
- 설명이 쉬운 상품 유리
- 저관여 생활불편 해결 상품 적합
- 고가, 옵션복잡, AS필요 상품 불리
"""
    }
}

RISKY_WORDS = [
    "정품", "명품", "나이키", "아디다스", "샤넬", "구찌", "디올",
    "루이비통", "카카오", "디즈니", "포켓몬", "산리오", "애플",
    "삼성", "LG", "엘지", "특허", "의료기기", "치료", "효능",
    "다이어트", "혈당", "당뇨", "탈모", "관절염", "통증완화",
    "약", "복용", "질병", "항균", "살균", "인증"
]

BAD_CATEGORY_HINTS = [
    "전자", "가전", "의료", "건강기능", "식품", "화장품",
    "배터리", "충전기", "칼", "공구", "유리", "도자기"
]

# =====================================================
# Gemini 호출
# =====================================================

def ask_ai(prompt, temperature=0.3):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 없습니다.")

    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": temperature,
            "response_mime_type": "application/json"
        }
    )

    return response.text


def extract_json(text):
    try:
        text = text.replace("```json", "").replace("```", "").strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
        return json.loads(text)
    except Exception:
        return None


# =====================================================
# AI 메인 MD: 시장 판단 + 키워드 발굴
# =====================================================

def ai_market_and_keywords(today_context, keyword_count=20):
    prompt = f"""
너는 온라인 위탁판매 월매출 천만원 이상 AI 메인 MD다.

아래 상황을 기준으로 오늘 도매매에서 찾아볼 만한 상품 키워드를 뽑아라.

조건:
- 스마트스토어, 옥션/지마켓, 토스쇼핑 모두 고려
- 브랜드명, 캐릭터명, 상표 위험 키워드 제외
- 도매매에서 검색했을 때 상품이 나올 만한 키워드
- 생활불편 해결형, 계절성, 저가 충동구매, CS 적은 상품 중심
- 너무 추상적인 키워드 금지
- 전자제품, 의료/건강 효능 상품, 식품, 화장품은 되도록 제외
- 네이버 검색어가 아니라 도매매 검색용 키워드로 변환
- 키워드는 {keyword_count}개

현재 상황:
{today_context}

반드시 아래 JSON 형식으로만 답해.

{{
  "market_summary": "오늘 시장 판단 요약",
  "target_categories": ["카테고리1", "카테고리2", "카테고리3"],
  "keywords": [
    {{
      "keyword": "검색키워드",
      "reason": "이 키워드를 고른 이유",
      "platform_fit": "스마트스토어/옥션지마켓/토스쇼핑 중 적합 플랫폼"
    }}
  ]
}}
"""

    try:
        result = ask_ai(prompt, temperature=0.45)
        data = extract_json(result)
    except Exception:
        data = None

    if not data:
        return {
            "market_summary": "AI 시장 분석 파싱 실패. 기본 키워드로 진행합니다.",
            "target_categories": ["생활용품", "차량용품", "수납용품"],
            "keywords": [
                {"keyword": "차량용선풍기", "reason": "초여름 차량용 수요", "platform_fit": "옥션/지마켓"},
                {"keyword": "냉감패드", "reason": "여름 시즌성", "platform_fit": "스마트스토어"},
                {"keyword": "압축수납팩", "reason": "생활불편 해결", "platform_fit": "토스쇼핑"},
                {"keyword": "욕실방수테이프", "reason": "저가 생활용품", "platform_fit": "스마트스토어"},
                {"keyword": "우산꽂이", "reason": "장마 준비", "platform_fit": "옥션/지마켓"}
            ]
        }

    return data


# =====================================================
# 도매매 상품 검색
# =====================================================

def search_domeme(keyword, limit=20, debug=False):
    if not DOMEME_API_KEY or not DOMEME_SEARCH_URL:
        if debug:
            st.warning("DOMEME_API_KEY 또는 DOMEME_SEARCH_URL이 없어 샘플상품으로 실행됩니다.")
        return sample_products(keyword, limit)

    params = {
        "apiKey": DOMEME_API_KEY,
        "keyword": keyword,
        "page": 1,
        "size": limit
    }

    try:
        res = requests.get(DOMEME_SEARCH_URL, params=params, timeout=20)
        res.raise_for_status()

        try:
            data = res.json()
        except Exception:
            st.error("도매매 응답이 JSON 형식이 아닙니다.")
            st.text(res.text[:3000])
            return []

        if debug:
            with st.expander(f"도매매 원본 응답 보기: {keyword}", expanded=False):
                st.write("요청 URL")
                st.code(res.url)
                st.write("응답 JSON")
                st.json(data)

        items = extract_items_from_response(data)

        if debug:
            st.write(f"'{keyword}' 추출 상품 수: {len(items)}개")
            if items:
                with st.expander(f"첫 번째 상품 원본 보기: {keyword}", expanded=False):
                    st.json(items[0])

        return [normalize_product(item, keyword) for item in items[:limit]]

    except Exception as e:
        st.warning(f"도매매 API 오류: {keyword} / {e}")
        return []


def extract_items_from_response(data):
    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    candidate_keys = [
        "items", "products", "data", "result", "goods", "list",
        "item", "product", "rows", "content", "body"
    ]

    for key in candidate_keys:
        value = data.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            for inner_key in candidate_keys:
                inner_value = value.get(inner_key)
                if isinstance(inner_value, list):
                    return inner_value

    # 혹시 data 내부 깊은 곳에 list가 있을 때 자동 탐색
    found = find_first_list(data)
    return found if found else []


def find_first_list(obj):
    if isinstance(obj, list):
        return obj

    if isinstance(obj, dict):
        for value in obj.values():
            result = find_first_list(value)
            if isinstance(result, list) and result:
                return result

    return []


def pick_first(item, keys, default=""):
    for key in keys:
        value = item.get(key)
        if value not in [None, "", "null"]:
            return value
    return default


def normalize_product(item, keyword):
    if not isinstance(item, dict):
        item = {}

    product_no = pick_first(item, [
        "productNo", "goodsNo", "itemNo",
        "goods_no", "product_no", "item_no",
        "goodsCode", "goodsCd", "goods_code",
        "productCode", "productCd", "product_code",
        "prdNo", "prdCd", "prdCode", "prd_no", "prd_cd",
        "no", "id", "code", "idx"
    ])

    name = pick_first(item, [
        "productName", "goodsName", "itemName",
        "goods_name", "product_name", "item_name",
        "goodsNm", "productNm", "prdNm", "prdName",
        "name", "title"
    ])

    supply_price = to_int(pick_first(item, [
        "supplyPrice", "supply_price",
        "price", "goodsPrice", "goods_price",
        "salePrice", "sale_price",
        "sellPrice", "sellingPrice",
        "consumerPrice", "cost",
        "prdPrice", "prd_price"
    ], 0))

    shipping_fee = to_int(pick_first(item, [
        "shippingFee", "deliveryFee",
        "delivery_price", "shipping_price",
        "deliveryPrice", "shipFee",
        "dlvFee", "dlv_fee"
    ], 3000))

    category = str(pick_first(item, [
        "category", "categoryName", "cateName",
        "category_name", "cate_name",
        "catename", "cateNm", "categoryNm"
    ], ""))

    image = str(pick_first(item, [
        "image", "imageUrl", "thumbnail",
        "mainImage", "main_image",
        "imgUrl", "img_url",
        "goodsImage", "goods_image"
    ], ""))

    return {
        "keyword": keyword,
        "product_no": str(product_no),
        "name": str(name),
        "supply_price": supply_price,
        "shipping_fee": shipping_fee,
        "category": category,
        "image": image,
        "raw": item
    }


def sample_products(keyword, limit=10):
    sample = []
    for i in range(1, limit + 1):
        sample.append({
            "keyword": keyword,
            "product_no": f"SAMPLE-{keyword}-{i}",
            "name": f"{keyword} 생활편의 샘플상품 {i}",
            "supply_price": 1200 + i * 650,
            "shipping_fee": 3000,
            "category": "생활/잡화",
            "image": "",
            "raw": {}
        })
    return sample


# =====================================================
# 계산/필터
# =====================================================

def to_int(value):
    try:
        return int(float(str(value).replace(",", "").replace("원", "").strip()))
    except Exception:
        return 0


def has_risky_word(text):
    text_lower = str(text).lower()
    return any(word.lower() in text_lower for word in RISKY_WORDS)


def has_bad_category(category, name):
    combined = f"{category} {name}"
    return any(word in combined for word in BAD_CATEGORY_HINTS)


def pre_filter(product):
    name = product["name"]
    category = product["category"]
    supply_price = product["supply_price"]
    shipping_fee = product["shipping_fee"]

    if not name:
        return False, "상품명 없음"

    if len(name) < 3:
        return False, "상품명 부실"

    if has_risky_word(name):
        return False, "상표/금지어 의심"

    if has_bad_category(category, name):
        return False, "초기버전 제외 카테고리"

    if supply_price <= 0:
        return False, "공급가 오류"

    if supply_price > 30000:
        return False, "공급가 과도"

    if shipping_fee > 5000:
        return False, "배송비 과도"

    return True, "통과"


def calc_platform_price(supply_price, shipping_fee, platform):
    rule = PLATFORM_RULES[platform]
    fee = rule["fee"]
    min_price = rule["min_price"]
    target_margin_rate = rule["target_margin_rate"]

    cost = supply_price + shipping_fee
    raw_price = cost / (1 - fee - target_margin_rate)
    price = math.ceil(raw_price / 100) * 100

    if price < min_price:
        price = min_price

    margin = int(price - (price * fee) - cost)
    margin_rate = round((margin / price) * 100, 1) if price > 0 else 0

    return price, margin, margin_rate


# =====================================================
# AI 플랫폼별 MD 평가
# =====================================================

def ai_md_evaluate(product, platform):
    price, margin, margin_rate = calc_platform_price(
        product["supply_price"],
        product["shipping_fee"],
        platform
    )

    prompt = f"""
아래 도매매 상품을 {platform} MD 기준으로 평가해라.

{PLATFORM_RULES[platform]["md_standard"]}

상품 정보:
- 상품번호: {product["product_no"]}
- 검색 키워드: {product["keyword"]}
- 상품명: {product["name"]}
- 카테고리: {product["category"]}
- 공급가: {product["supply_price"]}원
- 배송비: {product["shipping_fee"]}원
- 추천판매가: {price}원
- 예상마진: {margin}원
- 마진율: {margin_rate}%

평가 기준:
1. 판매 가능성
2. 검색 키워드 적합도
3. 가격 경쟁력
4. 무료배송 가능성
5. 충동구매 가능성
6. CS 위험도
7. 옵션 복잡도
8. 상표권/브랜드 위험
9. 썸네일 CTR 개선 가능성
10. 월천 셀러라면 등록할지 여부

점수 기준:
- 85점 이상: 강력추천
- 70~84점: 추천
- 55~69점: 보류
- 54점 이하: 제외

반드시 JSON 형식으로만 답해.

{{
  "score": 0,
  "decision": "강력추천/추천/보류/제외",
  "reason": "짧은 판단 이유",
  "platform_title": "플랫폼용 검색형 상품명",
  "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"],
  "risk": "위험요소",
  "selling_point": "판매 포인트",
  "thumbnail_text": "썸네일에 넣을 짧은 문구"
}}
"""

    try:
        result = ask_ai(prompt, temperature=0.2)
        data = extract_json(result)
        if not data:
            raise ValueError("JSON 파싱 실패")
    except Exception:
        data = {
            "score": 50,
            "decision": "보류",
            "reason": "AI 응답 파싱 실패. 수동 확인 필요.",
            "platform_title": product["name"],
            "tags": [],
            "risk": "확인 필요",
            "selling_point": "확인 필요",
            "thumbnail_text": ""
        }

    return {
        "platform": platform,
        "keyword": product["keyword"],
        "product_no": product["product_no"],
        "name": product["name"],
        "category": product["category"],
        "supply_price": product["supply_price"],
        "shipping_fee": product["shipping_fee"],
        "recommend_price": price,
        "margin": margin,
        "margin_rate": margin_rate,
        "ai_score": int(data.get("score", 0)),
        "decision": data.get("decision", "보류"),
        "reason": data.get("reason", ""),
        "platform_title": data.get("platform_title", product["name"]),
        "tags": ", ".join(data.get("tags", [])),
        "risk": data.get("risk", ""),
        "selling_point": data.get("selling_point", ""),
        "thumbnail_text": data.get("thumbnail_text", "")
    }


# =====================================================
# Streamlit UI
# =====================================================

st.title("월천셀러 AI MD 도매매 상품발굴기")
st.caption("Gemini AI가 시장 판단 → 키워드 발굴 → 도매매 상품 수집 → 플랫폼별 MD 점수화까지 진행합니다.")

with st.sidebar:
    st.header("실행 설정")

    today_context = st.text_area(
        "AI 메인 MD에게 줄 오늘 상황",
        value="""
현재 시기: 5월~6월
시장 상황: 초여름, 장마 준비, 차량용품, 수납, 욕실, 생활불편 해결 상품 수요 증가
판매 방향: 저가 충동구매, 무료배송 가능, CS 적은 상품, 상표권 위험 낮은 상품 위주
제외 방향: 전자제품, 의료/건강효능 상품, 식품, 화장품, 브랜드성 상품
""",
        height=180
    )

    keyword_count = st.slider("AI가 찾을 키워드 수", 5, 40, 20)
    product_limit = st.slider("키워드당 도매매 상품 수", 5, 50, 10)
    top_n = st.slider("최종 TOP 개수", 5, 50, 15)

    platforms = st.multiselect(
        "평가 플랫폼",
        ["스마트스토어", "옥션/지마켓", "토스쇼핑"],
        default=["스마트스토어", "옥션/지마켓", "토스쇼핑"]
    )

    manual_keywords = st.text_input(
        "추가 키워드가 있으면 입력",
        placeholder="예: 차량용선풍기, 냉감패드"
    )

    debug_api = st.checkbox("도매매 원본 응답 보기", value=False)

    run_btn = st.button("오늘 팔릴 상품 AI MD가 찾기", type="primary")


if run_btn:
    if not GEMINI_API_KEY:
        st.error("GEMINI_API_KEY가 없습니다. Streamlit Secrets 또는 .env에 넣어주세요.")
        st.stop()

    if not platforms:
        st.error("평가할 플랫폼을 최소 1개 선택하세요.")
        st.stop()

    with st.spinner("Gemini AI 메인 MD가 오늘 시장과 키워드를 판단 중..."):
        market_data = ai_market_and_keywords(today_context, keyword_count)

        keyword_items = market_data.get("keywords", [])
        keywords = []

        for item in keyword_items:
            if isinstance(item, dict):
                kw = item.get("keyword", "").strip()
            else:
                kw = str(item).strip()

            if kw:
                keywords.append(kw)

        if manual_keywords:
            extra = [
                k.strip()
                for k in manual_keywords.replace("\n", ",").split(",")
                if k.strip()
            ]
            keywords.extend(extra)

        keywords = list(dict.fromkeys(keywords))

    st.subheader("1. AI 메인 MD 시장 판단")
    st.write(market_data.get("market_summary", ""))

    st.write("타깃 카테고리")
    st.write(market_data.get("target_categories", []))

    st.subheader("2. AI가 선정한 도매매 검색 키워드")
    st.write(keywords)

    if not keywords:
        st.warning("키워드가 없습니다.")
        st.stop()

    all_products = []
    filtered_logs = []

    with st.spinner("도매매 상품 수집 및 1차 필터링 중..."):
        for keyword in keywords:
            products = search_domeme(keyword, product_limit, debug=debug_api)

            for product in products:
                passed, reason = pre_filter(product)

                if passed:
                    all_products.append(product)
                else:
                    filtered_logs.append({
                        "keyword": keyword,
                        "product_no": product.get("product_no", ""),
                        "name": product.get("name", ""),
                        "category": product.get("category", ""),
                        "supply_price": product.get("supply_price", 0),
                        "shipping_fee": product.get("shipping_fee", 0),
                        "reason": reason
                    })

    st.subheader("3. 1차 필터 결과")
    st.write(f"통과 상품: {len(all_products)}개 / 제외 상품: {len(filtered_logs)}개")

    if len(all_products) == 0:
        st.warning("1차 필터를 통과한 상품이 없습니다.")
        if filtered_logs:
            st.dataframe(pd.DataFrame(filtered_logs), use_container_width=True)
        st.stop()

    results = []
    total = len(all_products) * len(platforms)
    progress = st.progress(0)
    count = 0

    st.subheader("4. 플랫폼별 AI MD 점수화")

    for product in all_products:
        for platform in platforms:
            evaluated = ai_md_evaluate(product, platform)
            results.append(evaluated)

            count += 1
            progress.progress(count / total)

    df = pd.DataFrame(results)

    decision_rank = {
        "강력추천": 4,
        "추천": 3,
        "등록추천": 3,
        "추천함": 3,
        "보류": 2,
        "제외": 1
    }

    df["decision_rank"] = df["decision"].map(decision_rank).fillna(2)

    df = df.sort_values(
        by=["decision_rank", "ai_score", "margin_rate", "margin"],
        ascending=False
    )

    final_df = df[df["decision"].isin(["강력추천", "추천", "등록추천", "추천함"])].copy()

    if final_df.empty:
        final_df = df.copy()

    final_df = final_df.sort_values(
        by=["ai_score", "margin_rate", "margin"],
        ascending=False
    ).head(top_n)

    st.success("AI MD 분석 완료")

    columns = [
        "platform", "product_no", "keyword", "name", "category",
        "supply_price", "shipping_fee", "recommend_price",
        "margin", "margin_rate", "ai_score", "decision",
        "reason", "platform_title", "tags", "risk",
        "selling_point", "thumbnail_text"
    ]

    tabs = st.tabs([
        "최종 TOP",
        "스마트스토어",
        "옥션/지마켓",
        "토스쇼핑",
        "전체 데이터",
        "제외 상품"
    ])

    with tabs[0]:
        st.subheader("최종 TOP 상품")
        st.dataframe(final_df[columns], use_container_width=True)

        csv = final_df[columns].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "최종 TOP CSV 다운로드",
            data=csv,
            file_name="ai_md_top_products.csv",
            mime="text/csv"
        )

    for idx, platform in enumerate(["스마트스토어", "옥션/지마켓", "토스쇼핑"], start=1):
        with tabs[idx]:
            platform_df = df[df["platform"] == platform].sort_values(
                by=["ai_score", "margin_rate", "margin"],
                ascending=False
            ).head(top_n)

            st.subheader(f"{platform} MD 기준 TOP 상품")

            if platform_df.empty:
                st.info("해당 플랫폼 분석 데이터가 없습니다.")
            else:
                st.dataframe(platform_df[columns], use_container_width=True)

                platform_csv = platform_df[columns].to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    f"{platform} CSV 다운로드",
                    data=platform_csv,
                    file_name=f"ai_md_{platform}_products.csv".replace("/", "_"),
                    mime="text/csv"
                )

    with tabs[4]:
        st.subheader("전체 분석 데이터")
        st.dataframe(df[columns], use_container_width=True)

        all_csv = df[columns].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "전체 데이터 CSV 다운로드",
            data=all_csv,
            file_name="ai_md_all_products.csv",
            mime="text/csv"
        )

    with tabs[5]:
        st.subheader("1차 제외 상품")
        if filtered_logs:
            st.dataframe(pd.DataFrame(filtered_logs), use_container_width=True)
        else:
            st.info("제외 상품이 없습니다.")
