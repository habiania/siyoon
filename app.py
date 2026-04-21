import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

# --- [1. 설정 정보] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
DOME_ID = "sns@262783"
DOME_KEY = "69e11616807b334323c19d1a80cfd491"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="Gemini AI 시즌 소싱 마스터", layout="wide")

# --- [2. 핵심 함수: 도매매 수집 (보안/인증 강화 버전)] ---
def fetch_dome_data(keyword, limit=10):
    # 도매매 API 호출 URL
    url = "http://openapi.domeggook.com/helper/api/itemList"
    
    params = {
        "ver": "2.0",
        "mode": "getItemList",
        "aid": DOME_KEY,  # 도매매 API는 aid 자리에 발급받은 '인증키'를 넣어야 하는 경우가 많습니다.
        "market": "dome",
        "sw": keyword,    # 검색어
        "sz": limit,      # 검색 결과 수
        "sort": "reg"     # 최신등록순(reg)으로 변경하여 데이터 유무 확인
    }
    
    try:
        res = requests.get(url, params=params)
        # API 응답 확인 (디버깅용)
        if res.status_code != 200:
            return pd.DataFrame()
            
        root = ET.fromstring(res.content)
        
        # 도매매 API 에러 메시지 체크
        message = root.find(".//message")
        if message is not None and message.text != "OK":
            st.warning(f"도매매 응답: {message.text}")
            return pd.DataFrame()

        items = []
        for item in root.findall(".//item"):
            try:
                items.append({
                    "상품코드": item.find("no").text if item.find("no") is not None else "N/A",
                    "원본상품명": item.find("title").text if item.find("title") is not None else "이름없음",
                    "공급가": int(item.find("price").text) if item.find("price") is not None else 0,
                    "이미지": item.find("img").text if item.find("img") is not None else ""
                })
            except:
                continue
                
        return pd.DataFrame(items)
    except Exception as e:
        st.error(f"수집 중 오류 발생: {e}")
        return pd.DataFrame()

# --- [3. 핵심 함수: 제미나이 가공] ---
def ai_process(row, margin, fee):
    prompt = f"""
    너는 온라인 위탁판매 전문가야. 오늘 날짜는 {today_str}이야.
    다음 상품을 한국 소비자가 좋아하도록 가공해줘.
    
    [원본상품명] {row['원본상품명']}
    [공급원가] {row['공급가']}원
    
    미션:
    1. 상품명: 브랜드/상표권 단어는 삭제하고, {today_str} 시즌에 맞는 검색 키워드를 조합해 25자 내로 지어줘.
    2. 가격: 수수료 {fee*100}%와 마진 {margin*100}%를 계산해서, 끝자리가 800원이나 900원으로 끝나는 최적가를 숫자로만 제안해줘.
    
    출력 형식:
    이름: (가공된이름)
    가격: (숫자만)
    """
    try:
        response = model.generate_content(prompt)
        txt = response.text
        name_match = re.search(r"이름:\s*(.*)", txt)
        price_match = re.search(r"가격:\s*([\d,]+)", txt)
        
        name = name_match.group(1).strip() if name_match else row['원본상품명']
        price_str = price_match.group(1).replace(",", "") if price_match else str(int(row['공급가']*1.3))
        return name, int(price_str)
    except:
        return f"[시즌추천] {row['원본상품명'][:15]}", int(row['공급가'] * 1.3)

# --- [4. 메인 화면] ---
st.title(f" Gemini AI 시즌 소싱 ({today_str})")
st.sidebar.header("⚙️ 전략 설정")
target_margin = st.sidebar.slider("순마진율 (%)", 5, 50, 25) / 100
market_fee = 0.066 

search_keyword = st.text_input("소싱 키워드 (입력 후 아래 버튼 클릭)", value="양말")

if st.button(f"🔥 {search_keyword} 10개 수집 및 가공 시작"):
    with st.spinner("상품 데이터를 불러오는 중..."):
        raw_df = fetch_dome_data(search_keyword, 10)
        
        if not raw_df.empty:
            processed_results = []
            bar = st.progress(0)
            for i, row in raw_df.iterrows():
                new_name, new_price = ai_process(row, target_margin, market_fee)
                profit = new_price - row['공급가'] - (new_price * market_fee)
                processed_results.append({
                    "가공상품명": new_name,
                    "AI추천가": f"{new_price:,}원",
                    "예상순익": f"{int(profit):,}원"
                })
                bar.progress((i + 1) / len(raw_df))
            
            final_df = pd.concat([raw_df, pd.DataFrame(processed_results)], axis=1)
            st.success("✅ 가공 완료!")
            st.dataframe(final_df[["상품코드", "원본상품명", "공급가", "가공상품명", "AI추천가", "예상순익"]], use_container_width=True)
            
            st.subheader("🖼️ 상품 썸네일 미리보기")
            cols = st.columns(5)
            for i, row in raw_df.iterrows():
                with cols[i % 5]:
                    if row['이미지']:
                        st.image(row['이미지'], caption=row['상품코드'])
        else:
            st.error("데이터를 가져오지 못했습니다. 도매매 API 키 활성화 여부를 확인하거나 검색어를 바꿔보세요.")
