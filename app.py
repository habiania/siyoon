import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# --- [1. 설정 정보] ---
OPENAI_KEY = "sk-..." # 사장님의 OpenAI 키
DOME_ID = "사장님_도매매_아이디" # 도매매 ID 입력
DOME_KEY = "69e11616807b334323c19d1a80cfd491"

client = OpenAI(api_key=OPENAI_KEY)
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="AI 시즌 소싱 마스터", layout="wide")

# --- [2. 핵심 함수: 도매매 수집] ---
def fetch_dome_data(keyword, limit=10):
    url = "http://openapi.domeggook.com/helper/api/itemList"
    params = {
        "ver": "2.0",
        "mode": "getItemList",
        "aid": DOME_KEY,
        "market": "dome",
        "sw": keyword,
        "sz": limit,
        "sort": "pms" # 인기순
    }
    try:
        res = requests.get(url, params=params)
        root = ET.fromstring(res.content)
        items = []
        for item in root.findall(".//item"):
            items.append({
                "상품코드": item.find("no").text,
                "원본상품명": item.find("title").text,
                "공급가": int(item.find("price").text),
                "이미지": item.find("img").text
            })
        return pd.DataFrame(items)
    except:
        return pd.DataFrame()

# --- [3. 핵심 함수: AI 가공] ---
def ai_process(row, margin, fee):
    prompt = f"""
    오늘 날짜는 {today_str}이야. 온라인 위탁판매 전문가로서 행동해줘.
    [상품명] {row['원본상품명']} / [원가] {row['공급가']}원
    1. 상품명: 상표권 위험 단어는 지우고, 4월 말~5월 초 시즌 유입 키워드를 넣어 25자 내로 지어줘.
    2. 가격: 수수료 {fee*100}%와 마진 {margin*100}%를 감안해 역산한 뒤, 심리적 최적가(끝자리 900원 등)를 정해줘.
    형식: 이름: (새이름) / 가격: (숫자)
    """
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
        txt = res.choices[0].message.content
        name = txt.split("이름:")[1].split("/")[0].strip()
        price = int(txt.split("가격:")[1].strip().replace(",",""))
        return name, price
    except:
        return f"[시즌] {row['원본상품명']}", int(row['공급가'] * 1.3)

# --- [4. 메인 화면] ---
st.title(f"📅 {today_str} AI 시즌 소싱")
st.sidebar.header("⚙️ 전략 설정")
target_margin = st.sidebar.slider("순마진율 (%)", 5, 50, 25) / 100
market_fee = 0.066 # 6.6% 고정

# AI의 시즌 추천 테마
suggested_theme = "어버이날 카네이션 캠핑용품 나들이" 
search_keyword = st.text_input("소싱 키워드 (AI 추천: 어버이날, 캠핑, 선글라스)", value="어버이날")

if st.button(f"🚀 {search_keyword} 관련 상품 10개 수집 및 AI 가공"):
    with st.spinner("도매매에서 상품을 긁어오고 AI가 분석 중..."):
        raw_df = fetch_dome_data(search_keyword, 10)
        
        if not raw_df.empty:
            processed_results = []
            for _, row in raw_df.iterrows():
                new_name, new_price = ai_process(row, target_margin, market_fee)
                profit = new_price - row['공급가'] - (new_price * market_fee)
                processed_results.append({
                    "가공상품명": new_name,
                    "AI추천가": f"{new_price:,}원",
                    "예상수익": f"{int(profit):,}원"
                })
            
            final_df = pd.concat([raw_df, pd.DataFrame(processed_results)], axis=1)
            st.success("✅ 시즌 맞춤 가공 완료!")
            st.dataframe(final_df[["상품코드", "원본상품명", "공급가", "가공상품명", "AI추천가", "예상수익"]], use_container_width=True)
            
            # 이미지 보기 기능 추가
            st.subheader("🖼️ 상품 썸네일 미리보기")
            cols = st.columns(5)
            for i, row in raw_df.head(10).iterrows():
                with cols[i % 5]:
                    st.image(row['이미지'], caption=row['상품코드'])
        else:
            st.error("도매매에서 상품을 가져오지 못했습니다. 키워드나 API키를 확인하세요.")
