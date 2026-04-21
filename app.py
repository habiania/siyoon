import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

# --- [1. 설정 정보] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
DOME_KEY = "69e11616807b334323c19d1a80cfd491"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="Gemini AI 시즌 소싱 마스터", layout="wide")

# --- [2. 핵심 함수: 도매매 수집 (글자 깨짐 방지 추가)] ---
def fetch_dome_data(keyword, limit=10):
    url = "http://openapi.domeggook.com/helper/api/itemList"
    params = {
        "ver": "2.0",
        "mode": "getItemList",
        "aid": DOME_KEY,
        "market": DOME_ID,  #
        "sw": keyword,    
        "sz": limit,      
        "sort": "reg"     
    }
    
    try:
        res = requests.get(url, params=params)
        
        # [핵심 수정] 도매매 특유의 글자 인코딩(EUC-KR) 처리
        # 만약 UTF-8로 읽어서 에러가 나면 EUC-KR로 읽도록 시도합니다.
        try:
            content = res.content.decode('utf-8')
        except UnicodeDecodeError:
            content = res.content.decode('euc-kr', errors='replace')
        
        # XML 해석
        root = ET.fromstring(content)
        
        # 도매매 응답 메시지 확인
        msg_node = root.find(".//message")
        if msg_node is not None and msg_node.text != "OK":
            st.error(f"도매매 응답: {msg_node.text}")
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
            except: continue
                
        return pd.DataFrame(items)
    except Exception as e:
        st.error(f"데이터 처리 중 오류: {e}")
        return pd.DataFrame()

# --- [3. 핵심 함수: 제미나이 가공] ---
def ai_process(row, margin, fee):
    prompt = f"""
    너는 온라인 위탁판매 전문가야. 오늘 날짜는 {today_str}이야.
    [원본상품명] {row['원본상품명']} / [공급원가] {row['공급가']}원
    미션: 브랜드/상표권 단어는 삭제하고 한국 소비자가 좋아할만한 25자 내외의 상품명을 지어줘.
    가격은 수수료 {fee*100}%와 마진 {margin*100}%를 계산해서 끝자리가 800/900원인 최적가 숫자로만 제안해.
    출력 형식: 이름: (가공된이름) / 가격: (숫자만)
    """
    try:
        response = model.generate_content(prompt)
        txt = response.text
        # 이름과 가격 추출 로직 강화
        name = row['원본상품명']
        price = int(row['공급가'] * 1.3)
        
        if "이름:" in txt:
            name = txt.split("이름:")[1].split("/")[0].split("\n")[0].strip()
        if "가격:" in txt:
            price_raw = re.findall(r'\d+', txt.split("가격:")[1])[0]
            price = int(price_raw)
            
        return name, price
    except:
        return f"[시즌] {row['원본상품명'][:15]}", int(row['공급가'] * 1.3)

# --- [4. 메인 화면] ---
st.title(f"♊ Gemini AI 시즌 소싱 ({today_str})")
st.sidebar.header("⚙️ 전략 설정")
target_margin = st.sidebar.slider("순마진율 (%)", 5, 50, 25) / 100
market_fee = 0.066 

search_keyword = st.text_input("소싱 키워드", value="양말")

if st.button(f"🔥 {search_keyword} 10개 수집 및 가공 시작"):
    with st.spinner("데이터를 분석하고 가공하는 중..."):
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
            st.success("✅ 가공 성공!")
            st.dataframe(final_df[["상품코드", "원본상품명", "공급가", "가공상품명", "AI추천가", "예상순익"]], use_container_width=True)
            
            st.subheader("🖼️ 상품 썸네일")
            cols = st.columns(5)
            for i, row in raw_df.iterrows():
                with cols[i % 5]:
                    if row['이미지']: st.image(row['이미지'], caption=row['상품코드'])
        else:
            st.error("데이터를 가져오지 못했습니다. 도매매 사이트에서 API 키가 '사용중'인지 확인해 주세요.")
