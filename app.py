import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

# --- [1. 설정 정보] ---
# 사장님이 주신 제미나이 API 키 적용 완료
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
DOME_ID = "sns@262783"
DOME_KEY = "69e11616807b334323c19d1a80cfd491"

# 제미나이 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="Gemini AI 시즌 소싱 마스터", layout="wide")

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
        "sort": "pms"
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

# --- [3. 핵심 함수: 제미나이 가공] ---
def ai_process(row, margin, fee):
    prompt = f"""
    너는 온라인 위탁판매 전문가야. 오늘 날짜는 {today_str}이야.
    다음 상품을 한국 소비자가 좋아하도록 가공해줘.
    
    [원본상품명] {row['원본상품명']}
    [공급원가] {row['공급가']}원
    
    미션:
    1. 상품명: 상표권 위험 단어는 삭제하고, 지금 시즌({today_str})에 맞는 키워드를 넣어 25자 내로 매력적으로 지어줘.
    2. 가격: 수수료 {fee*100}%와 마진 {margin*100}%를 계산해서, 소비자가 '싸다'고 느낄 끝자리 900원 혹은 800원 단위의 가격을 정해줘.
    
    출력 형식:
    이름: (가공된이름)
    가격: (숫자만)
    """
    try:
        response = model.generate_content(prompt)
        txt = response.text
        # 정규표현식으로 이름과 가격 추출
        name_match = re.search(r"이름:\s*(.*)", txt)
        price_match = re.search(r"가격:\s*([\d,]+)", txt)
        
        name = name_match.group(1).strip() if name_match else row['원본상품명']
        price_str = price_match.group(1).replace(",", "") if price_match else str(int(row['공급가']*1.3))
        return name, int(price_str)
    except:
        return f"[시즌] {row['원본상품명']}", int(row['공급가'] * 1.3)

# --- [4. 메인 화면] ---
st.title(f"♊ Gemini AI 시즌 소싱 ({today_str})")
st.markdown("### 🚀 오늘 날짜 기반 지능형 상품 가공 시스템")

st.sidebar.header("⚙️ 전략 설정")
target_margin = st.sidebar.slider("순마진율 (%)", 5, 50, 25) / 100
market_fee = 0.066 # 6.6%

search_keyword = st.text_input("소싱 키워드 (AI 추천: 카네이션, 어버이날, 캠핑용품)", value="어버이날")

if st.button(f"🔥 {search_keyword} 10개 수집 및 Gemini 가공 시작"):
    with st.spinner("구글 제미나이가 상품을 분석 중입니다..."):
        raw_df = fetch_dome_data(search_keyword, 10)
        
        if not raw_df.empty:
            processed_results = []
            for _, row in raw_df.iterrows():
                new_name, new_price = ai_process(row, target_margin, market_fee)
                profit = new_price - row['공급가'] - (new_price * market_fee)
                processed_results.append({
                    "가공상품명": new_name,
                    "AI추천가": f"{new_price:,}원",
                    "예상순익": f"{int(profit):,}원"
                })
            
            final_df = pd.concat([raw_df, pd.DataFrame(processed_results)], axis=1)
            st.success("✅ Gemini 지능형 가공 완료!")
            
            # 결과 테이블 출력
            st.dataframe(final_df[["상품코드", "원본상품명", "공급가", "가공상품명", "AI추천가", "예상순익"]], use_container_width=True)
            
            # 이미지 갤러리
            st.subheader("🖼️ 상품 썸네일 미리보기")
            cols = st.columns(5)
            for i, row in raw_df.iterrows():
                with cols[i % 5]:
                    st.image(row['이미지'], caption=row['상품코드'])
        else:
            st.error("데이터를 가져오지 못했습니다. 키워드를 변경하거나 잠시 후 다시 시도하세요.")
