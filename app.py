import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import time
import hmac
import hashlib
import base64
import re
from datetime import datetime

# --- [1. 설정 정보] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
NAVER_CLIENT_ID = "1mrpP8IsCpfwnfvDfci2up"
# [중요] 반드시 재발급받은 최신 시크릿 값을 아래에 넣으세요!
NAVER_CLIENT_SECRET = "$2a$04$x1.6V7Jjy9AbgkSHqK4wle" 

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="모던마켓2024 관리센터", layout="wide")

# --- [2. 핵심 함수: 네이버 인증 (가장 정석적인 방식)] ---
def get_naver_token():
    timestamp = str(int(time.time() * 1000))
    # Signature 생성 로직
    password = f"{NAVER_CLIENT_ID}_{timestamp}"
    hashed = hmac.new(
        NAVER_CLIENT_SECRET.encode('utf-8'), 
        password.encode('utf-8'), 
        hashlib.sha256
    ).digest()
    signature = base64.b64encode(hashed).decode('utf-8')
    
    url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    
    # 네이버가 요구하는 x-www-form-urlencoded 데이터 포맷
    data = {
        "client_id": NAVER_CLIENT_ID,
        "timestamp": timestamp,
        "grant_type": "client_credentials",
        "client_secret_sign": signature,
        "type": "SELF"
    }
    
    try:
        # headers 없이 순수하게 data(form-data)로 전송하는 것이 네이버 표준입니다.
        res = requests.post(url, data=data)
        res_data = res.json()
        
        if "access_token" in res_data:
            return res_data.get("access_token")
        else:
            # 실패 시 네이버의 날것 그대로의 에러를 확인합니다.
            st.error(f"❌ 네이버 인증 실패: {res_data.get('message', '데이터 불일치')}")
            return None
    except Exception as e:
        st.error(f"📡 서버 연결 실패: {e}")
        return None

# --- [3. 상표권 검사 로직] ---
def check_trademark(name):
    prompt = f"상품명 '{name}'에 상표권 위반 위험이 있다면 [위험], 아니면 [안전]이라고 답하고 이유를 짧게 써줘."
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "분석 불가"

# --- [4. 화면 구성] ---
st.sidebar.title("🚀 모던마켓2024")
menu = st.sidebar.radio("작업", ["🛡️ 상표권 전수조사", "🎁 상품 소싱"])

if menu == "🛡️ 상표권 전수조사":
    st.header("🛡️ 실시간 상표권 모니터링")
    if st.button("🔍 내 스토어 상품 불러오기"):
        token = get_naver_token()
        if token:
            st.success("✅ 네이버 연결 성공!")
            # 상품 조회 API 호출
            url = "https://api.commerce.naver.com/external/v1/products/search"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            payload = {"page": 1, "size": 50}
            
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                products = res.json().get("contents", [])
                if not products:
                    st.info("등록된 상품이 없습니다.")
                else:
                    results = [{"상품명": p.get("name"), "진단": check_trademark(p.get("name"))} for p in products]
                    st.table(pd.DataFrame(results))
            else:
                st.warning("⚠️ 인증은 성공했으나 상품 정보를 가져올 수 없습니다. (권한 대기 중일 수 있음)")
