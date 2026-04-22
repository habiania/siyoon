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

# [수정 완료] 뒤에 붙어있던 날짜와 아이디 등 불순물을 모두 제거했습니다.
NAVER_CLIENT_SECRET = "$2a$04$IDSwLVb1Unbz6xSCiwn4rO" 

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="모던마켓2024 관리센터", layout="wide")

# --- [2. 핵심 함수: 네이버 인증] ---
def get_naver_token():
    timestamp = str(int(time.time() * 1000))
    password = f"{NAVER_CLIENT_ID}_{timestamp}"
    
    hashed = hmac.new(
        NAVER_CLIENT_SECRET.encode('utf-8'), 
        password.encode('utf-8'), 
        hashlib.sha256
    ).digest()
    
    signature = base64.b64encode(hashed).decode('utf-8')
    
    url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    data = {
        "client_id": NAVER_CLIENT_ID,
        "timestamp": timestamp,
        "grant_type": "client_credentials",
        "client_secret_sign": signature,
        "type": "SELF"
    }
    
    try:
        # 네이버 표준: x-www-form-urlencoded 방식으로 전송
        res = requests.post(url, data=data)
        res_data = res.json()
        if "access_token" in res_data:
            return res_data.get("access_token")
        else:
            st.error(f"❌ 네이버 응답: {res_data.get('message')}")
            return None
    except Exception as e:
        st.error(f"📡 연결 오류: {e}")
        return None

# --- [3. 화면 구성] ---
st.title("🛡️ 모던마켓2024 상표권 방어 시스템")

if st.button("🔍 내 스토어 상품 불러오기"):
    with st.spinner("네이버 서버와 통신 중..."):
        token = get_naver_token()
        if token:
            st.success("✅ 드디어 연결 성공! 상품 정보를 가져옵니다.")
            url = "https://api.commerce.naver.com/external/v1/products/search"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            payload = {"page": 1, "size": 30}
            
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                products = res.json().get("contents", [])
                if not products:
                    st.info("등록된 상품이 없습니다.")
                else:
                    df = pd.DataFrame([{"상품명": p.get("name"), "상품번호": p.get("originProductNo")} for p in products])
                    st.dataframe(df, use_container_width=True)
            else:
                st.warning("인증은 성공했으나 권한 설정이 대기 중일 수 있습니다.")
