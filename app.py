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
# 사장님이 새로 발급받은 '진짜' 시크릿 키입니다.
NAVER_CLIENT_SECRET = "$2a$04$IDSwLVb1Unbz6xSCiwn4rO2026-04-22" 

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="모던마켓2024 통합 관리 센터", layout="wide")

# --- [2. 핵심 함수: 네이버 인증 토큰] ---
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
    payload = {
        "client_id": NAVER_CLIENT_ID,
        "timestamp": timestamp,
        "grant_type": "client_credentials",
        "client_secret_sign": signature,
        "type": "SELF"
    }
    
    try:
        res = requests.post(url, data=payload)
        res_data = res.json()
        if "access_token" in res_data:
            return res_data.get("access_token")
        else:
            st.error(f"❌ 인증 실패 메시지: {res_data.get('message')}")
            return None
    except Exception as e:
        st.error(f"📡 연결 오류: {e}")
        return None

# --- [3. 핵심 함수: AI 상표권 검사] ---
def check_trademark(name):
    prompt = f"상품명 '{name}'에서 상표권 위반(유명 브랜드 사칭) 단어가 있으면 [위험], 없으면 [안전]이라고 답하고 이유를 짧게 써줘."
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "검사 불가"

# --- [4. 메인 화면 구성] ---
st.sidebar.title("🚀 모던마켓2024")
menu = st.sidebar.radio("작업 선택", ["🛡️ 상표권 전수조사", "🎁 상품 소싱"])

if menu == "🛡️ 상표권 전수조사":
    st.header("🛡️ 내 스토어 상표권 방패")
    if st.button("🔍 내 스토어 상품 불러오기"):
        token = get_naver_token()
        if token:
            st.success("✅ 네이버 인증 성공!")
            url = "https://api.commerce.naver.com/external/v1/products/search"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            payload = {"page": 1, "size": 30}
            
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                products = res.json().get("contents", [])
                if not products:
                    st.info("등록된 상품이 없습니다.")
                else:
                    results = []
                    for p in products:
                        name = p.get("name")
                        status = check_trademark(name)
                        results.append({"상품명": name, "AI 진단": status})
                    st.table(pd.DataFrame(results))
            else:
                st.warning("인증은 성공했으나 상품 정보를 가져올 수 없습니다. API 그룹 설정을 확인해 주세요.")

elif menu == "🎁 상품 소싱":
    st.header("🎁 AI 시즌 상품 소싱")
    st.info("도매매 API 승인 완료 후 사용 가능합니다.")
