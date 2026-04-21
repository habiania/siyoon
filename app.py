import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

# --- [1. 설정 정보] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
DOME_ID = "sns@262783"  # 사장님 아이디
DOME_KEY = "69e11616807b334323c19d1a80cfd491" # 사장님 인증키

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
        "aid": DOME_KEY,      # 인증키
        "id": DOME_ID,        # 아이디
        "market": "dome",     # 마켓 고정
        "sw": keyword,    
        "sz": limit,      
        "sort": "reg"     
    }
    
    try:
        res = requests.get(url, params=params)
        
        # 글자 깨짐 방지 처리
        try:
            content = res.content.decode('utf-8')
        except UnicodeDecodeError:
            content = res.content.decode('euc-kr', errors='replace')
        
        root = ET.fromstring(content)
        
        # 도매매 응답 메시지 확인
        msg_node = root.find(".//message")
        if msg_node is not None and msg_node.text != "OK":
            st.warning(f"도매매 알림: {msg_node.text}")
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
        st.error(f"연결 오류 발생: {e}")
        return pd.DataFrame()

# --- [3. 핵심 함수: 제미나이 가공] ---
def ai_process(row, margin, fee):
    prompt = f"""
    온라인 쇼핑몰 전문가로서 상품명을 가공해줘.
    [원본명] {row['원본상품명']} / [원가] {row['공급가']}원 / [날짜] {today_str}
    미션: 상표권 위험 단어는 빼고, 25자 내외의 세련된 한국어 상품명으로 바꿔줘. 
    가격은 수수료 {fee*100}%와 마진 {margin*100}%를 고려해 끝자리 900원 단위로 책정해줘.
    출력 형식: 이름: (이름) / 가격: (숫자)
    """
    try:
        response = model.generate_content(prompt)
        txt = response.text
        # 유연한 결과 추출
        name = row['원본상품명']
        price = int(row['공급가'] * 1.3)
        
        if "이름:" in txt:
            name = txt.split("이름:")[1].split("/")[0].split("\n")[0].strip()
        if "가격:" in txt:
            price_find = re.findall(r'\d+', txt.split("가격:")[1])
            if price_find: price = int(price_find[0])
            
        return name, price
    except:
        return row['원본상품명'], int(row['공급가'] * 1.3)

# --- [4. 메인 화면] ---
st.title(f"♊ Gemini AI 시즌 소싱 ({today_str})")
st.markdown("---")

st.sidebar.header("⚙️ 전략 설정")
target_margin = st.sidebar.slider("순마진율 (%)", 5, 50, 25) / 100
market_fee = 0.066 

keyword = st.text_input("검색할 키워드를 입력하세요", value="양말")

if st.button(f"🚀 '{keyword}' 분석 시작"):
    with st.spinner("상품 데이터를 분석하고 있습니다..."):
        df = fetch_dome_data(keyword, 10)
        
        if not df.empty:
            processed = []
            for _, row in df.iterrows():
                n, p = ai_process(row, target_margin, market_fee)
                profit = p - row['공급가'] - (p * market_fee)
                processed.append({"가공명": n, "AI가격": f"{p:,}원", "수익": f"{int(profit):,}원"})
            
            result = pd.concat([df, pd.DataFrame(processed)], axis=1)
            st.success("✅ 분석이 완료되었습니다!")
            st.dataframe(result[["상품코드", "원본상품명", "공급가", "가공명", "AI가격", "수익"]], use_container_width=True)
            
            st.subheader("🖼️ 상품 썸네일 미리보기")
            cols = st.columns(5)
            for i, row in df.iterrows():
                with cols[i % 5]:
                    if row['이미지']: st.image(row['이미지'], caption=row['상품코드'])
        else:
            st.error("데이터를 가져오지 못했습니다. 도매매 API 키가 '사용중' 상태인지 다시 확인해 주세요.")
