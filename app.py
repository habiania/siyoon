import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

# --- [1. 설정 정보] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
DOME_ID = "ryule1122"  
DOME_KEY = "7f476022a7670ce1f483b470c6b1aef9" 

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="Gemini AI 시즌 소싱 마스터", layout="wide")

# --- [2. 핵심 함수: 도매매 수집] ---
def fetch_dome_data(keyword, limit=10):
    # 도매매 API 표준 주소
    url = "http://openapi.domeggook.com/helper/api/itemList"
    
    params = {
        "ver": "2.0",
        "mode": "getItemList",
        "aid": DOME_KEY,      
        "id": DOME_ID,        
        "market": "dome",     
        "sw": keyword,    
        "sz": limit,      
        "sort": "reg"     
    }
    
    try:
        res = requests.get(url, params=params, timeout=10)
        # 도매매는 EUC-KR을 사용하므로 변환이 필수입니다.
        content = res.content.decode('euc-kr', errors='replace')
        
        # [진단] 서버 응답에 OK가 없는 경우 에러 메시지를 직접 파싱해서 보여줍니다.
        if "<message>OK</message>" not in content:
            root = ET.fromstring(res.content)
            err_msg = root.find(".//message").text if root.find(".//message") is not None else "알 수 없는 인증 오류"
            st.error(f"🚨 도매매 서버 거부 사유: {err_msg}")
            if "유효하지 않은" in err_msg:
                st.info("💡 해결방법: 도매매 API 센터에서 키 상태가 '사용중'인지, IP 제한이 없는지 다시 확인해주세요.")
            return pd.DataFrame()

        root = ET.fromstring(content)
        items = []
        for item in root.findall(".//item"):
            try:
                items.append({
                    "상품코드": item.find("no").text,
                    "원본상품명": item.find("title").text,
                    "공급가": int(item.find("price").text),
                    "이미지": item.find("img").text
                })
            except: continue
        return pd.DataFrame(items)
    except Exception as e:
        st.error(f"📡 연결 자체가 실패했습니다: {e}")
        return pd.DataFrame()

# --- [3. 핵심 함수: 제미나이 가공] ---
def ai_process(row, margin, fee):
    prompt = f"상품 '{row['원본상품명']}'(원가:{row['공급가']}원)을 위탁판매용으로 25자 내외로 작명하고 가격은 마진{margin*100}% 포함 끝자리 900원으로 책정해. 형식: 이름: (이름) / 가격: (숫자)"
    try:
        response = model.generate_content(prompt)
        txt = response.text
        name = re.search(r"이름:\s*(.*?)\s*/", txt).group(1).strip() if "이름:" in txt else row['원본상품명']
        price = re.search(r"가격:\s*([\d,]+)", txt).group(1).replace(",", "") if "가격:" in txt else str(int(row['공급가']*1.4))
        return name, int(price)
    except:
        return row['원본상품명'], int(row['공급가'] * 1.4)

# --- [4. 메인 화면] ---
st.title(f"♊ Gemini AI 시즌 소싱 ({today_str})")
st.sidebar.header("⚙️ 전략 설정")
target_margin = st.sidebar.slider("순마진율 (%)", 5, 50, 25) / 100
market_fee = 0.066 

keyword = st.text_input("소싱 키워드 입력", value="양말")

if st.button(f"🚀 '{keyword}' 분석 시작"):
    with st.spinner("도매매와 통신 중..."):
        df = fetch_dome_data(keyword, 10)
        
        if not df.empty:
            processed = []
            for _, row in df.iterrows():
                n, p = ai_process(row, target_margin, market_fee)
                profit = p - row['공급가'] - (p * market_fee)
                processed.append({"가공명": n, "AI가격": f"{p:,}원", "수익": f"{int(profit):,}원"})
            
            result = pd.concat([df, pd.DataFrame(processed)], axis=1)
            st.success("✅ 연결 성공 및 데이터 가공 완료!")
            st.dataframe(result[["상품코드", "원본상품명", "공급가", "가공명", "AI가격", "수익"]], use_container_width=True)
            
            cols = st.columns(5)
            for i, row in df.iterrows():
                with cols[i % 5]:
                    if row['이미지']: st.image(row['이미지'], caption=row['상품코드'])
