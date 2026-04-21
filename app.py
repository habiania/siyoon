import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

# --- [1. 설정 정보] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
DOME_KEY = "69e11616807b334323c19d1a80cfd491" # 사장님의 API 인증키

# 제미나이 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="Gemini AI 시즌 소싱 마스터", layout="wide")

# --- [2. 핵심 함수: 도매매 수집 (인증 방식 최적화)] ---
def fetch_dome_data(keyword, limit=10):
    # 도매매 API 주소
    url = "http://openapi.domeggook.com/helper/api/itemList"
    
    # 도매매 OPEN API는 보통 'aid' 파라미터에 발급받은 'API Key'를 바로 넣습니다.
    params = {
        "ver": "2.0",
        "mode": "getItemList",
        "aid": DOME_KEY,  # <--- 여기에 아이디 대신 인증키를 넣는 것이 표준입니다.
        "market": "dome",
        "sw": keyword,    
        "sz": limit,      
        "sort": "reg"     
    }
    
    try:
        res = requests.get(url, params=params)
        # 응답 내용을 텍스트로 확인 (디버깅)
        content = res.content.decode('utf-8')
        
        # 만약 결과가 없거나 에러가 나면 화면에 표시
        if "<message>OK</message>" not in content:
            # 에러 메시지 추출 시도
            root = ET.fromstring(res.content)
            msg = root.find(".//message")
            st.error(f"도매매 연결 문제: {msg.text if msg is not None else '인증 오류'}")
            return pd.DataFrame()

        root = ET.fromstring(res.content)
        items = []
        for item in root.findall(".//item"):
            items.append({
                "상품코드": item.find("no").text if item.find("no") is not None else "N/A",
                "원본상품명": item.find("title").text if item.find("title") is not None else "이름없음",
                "공급가": int(item.find("price").text) if item.find("price") is not None else 0,
                "이미지": item.find("img").text if item.find("img") is not None else ""
            })
                
        return pd.DataFrame(items)
    except Exception as e:
        st.error(f"연결 중 기술적 오류 발생: {e}")
        return pd.DataFrame()

# --- [3. 핵심 함수: 제미나이 가공] ---
def ai_process(row, margin, fee):
    prompt = f"""
    너는 온라인 위탁판매 전문가야. 오늘 날짜는 {today_str}이야.
    [원본상품명] {row['원본상품명']} / [공급원가] {row['공급가']}원
    미션: 상표권 위험 단어는 삭제하고 {today_str} 시즌에 맞는 검색 키워드를 조합해 25자 내로 상품명을 지어줘.
    가격은 수수료 {fee*100}%와 마진 {margin*100}%를 계산해서 끝자리가 800/900원인 최적가 숫자로만 제안해.
    출력 형식: 이름: (가공된이름) / 가격: (숫자만)
    """
    try:
        response = model.generate_content(prompt)
        txt = response.text
        name = re.search(r"이름:\s*(.*?)\s*/", txt).group(1).strip()
        price = re.search(r"가격:\s*([\d,]+)", txt).group(1).replace(",", "")
        return name, int(price)
    except:
        return f"[시즌] {row['원본상품명'][:15]}", int(row['공급가'] * 1.3)

# --- [4. 메인 화면] ---
st.title(f"♊ Gemini AI 시즌 소싱 ({today_str})")
st.sidebar.header("⚙️ 전략 설정")
target_margin = st.sidebar.slider("순마진율 (%)", 5, 50, 25) / 100
market_fee = 0.066 

search_keyword = st.text_input("소싱 키워드 (예: 양말, 캠핑, 선글라스)", value="양말")

if st.button(f"🔥 {search_keyword} 10개 수집 및 가공 시작"):
    with st.spinner("도매매에서 상품을 가져오고 있습니다..."):
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
            st.success("✅ 가공 완료!")
            st.dataframe(final_df[["상품코드", "원본상품명", "공급가", "가공상품명", "AI추천가", "예상순익"]], use_container_width=True)
            
            st.subheader("🖼️ 상품 이미지")
            cols = st.columns(5)
            for i, row in raw_df.iterrows():
                with cols[i % 5]:
                    if row['이미지']: st.image(row['이미지'], caption=row['상품코드'])
        else:
            st.error("데이터를 불러오지 못했습니다. 키워드를 바꿔보거나 잠시 후 다시 시도하세요.")
