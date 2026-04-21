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

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="Gemini AI 시즌 소싱 마스터", layout="wide")

# --- [2. 핵심 함수: 도매매 수집] ---
def fetch_dome_data(keyword, limit=10):
    url = "http://openapi.domeggook.com/helper/api/itemList"
    
    # 도매매 API 가이드에 맞춘 파라미터 재설정
    params = {
        "ver": "2.0",
        "mode": "getItemList",
        "aid": DOME_KEY,      # 인증키
        "id": DOME_ID,        # 아이디 추가
        "market": "dome",     # [중요] 변수가 아닌 문자열 "dome"으로 고정
        "sw": keyword,    
        "sz": limit,      
        "sort": "reg"     
    }
    
    try:
        res = requests.get(url, params=params)
        
        # 글자 깨짐 방지 (EUC-KR 처리)
        try:
            content = res.content.decode('utf-8')
        except UnicodeDecodeError:
            content = res.content.decode('euc-kr', errors='replace')
        
        root = ET.fromstring(content)
        
        # 에러 메시지 확인
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
        st.error(f"연결 오류: {e}")
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
        name = re.search(r"이름:\s*(.*?)\s*/", txt).group(1).strip() if "이름:" in txt else row['원본상품명']
        price = re.search(r"가격:\s*([\d,]+)", txt).group(1).replace(",", "") if "가격:" in txt else str(int(row['공급가']*1.3))
        return name, int(price)
    except:
        return row['원본상품명'], int(row['공급가'] * 1.3)

# --- [4. 메인 화면] ---
st.title(f"♊ Gemini AI 시즌 소싱 ({today_str})")
st.sidebar.header("⚙️ 전략 설정")
target_margin = st.sidebar.slider("순마진율 (%)", 5, 50, 25) / 100
market_fee = 0.066 

keyword = st.text_input("소싱 키워드 (예: 양말, 슬리퍼, 어버이날)", value="양말")

if st.button(f"🚀 {keyword} 상품 10개 분석 시작"):
    with st.spinner("도매매 데이터를 불러오고 있습니다..."):
        df = fetch_dome_data(keyword, 10)
        
        if not df.empty:
            processed = []
            for _, row in df.iterrows():
                n, p = ai_process(row, target_margin, market_fee)
                profit = p - row['공급가'] - (p * market_fee)
                processed.append({"가공명": n, "AI가격": f"{p:,}원", "수익": f"{int(profit):,}원"})
            
            result = pd.concat([df, pd.DataFrame(processed)], axis=1)
            st.success("✅ 분석 완료!")
            st.dataframe(result[["상품코드", "원본상품명", "공급가", "가공명", "AI가격", "수익"]], use_container_width=True)
            
            cols = st.columns(5)
            for i, row in df.iterrows():
                with cols[i % 5]:
                    if row['이미지']: st.image(row['이미지'], caption=row['상품코드'])
        else:
            st.error("데이터를 가져오지 못했습니다. 검색어를 바꾸거나 도매매 API 키 상태를 확인하세요.")
