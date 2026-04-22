import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import time
import hmac
import hashlib
import base64
from datetime import datetime

# --- [1. 설정 정보] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
NAVER_CLIENT_ID = "1mrpP8IsCpfwnfvDfci2up"

# [주의] 네이버 센터에서 [보기]를 눌러 나타나는 '진짜 긴 문자열'을 아래에 넣으세요.
NAVER_CLIENT_SECRET = "$2a$04$6ar.9OFzn.Jnm2GKYaxecO" 

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="모던마켓2024 통합센터", layout="wide")

# --- [2. 네이버 인증 함수] ---
def get_naver_token():
    timestamp = str(int(time.time() * 1000))
    # [수정 완료] 변수명을 사용하여 정확하게 호출하도록 고쳤습니다.
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
        res = requests.post(url, data=data)
        res_data = res.json()
        if "access_token" in res_data:
            return res_data.get("access_token")
        else:
            st.error(f"❌ 네이버 인증 실패: {res_data.get('message')}")
            return None
    except: return None

# --- [3. 상표권 검사 함수] ---
def check_trademark(name):
    prompt = f"상품명 '{name}'에 상표권 위반 위험이 있다면 [위험], 아니면 [안전]이라고 답하고 이유를 짧게 써줘."
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "분석 불가"

# --- [4. 메인 화면] ---
st.title("🛡️ 모던마켓2024 통합 관리 센터")
st.sidebar.title("메뉴")
menu = st.sidebar.radio("작업 선택", ["🛡️ 상표권 전수조사", "🎁 신규 상품 소싱"])

if menu == "🛡️ 상표권 전수조사":
    st.header("🔎 내 스토어 상표권 전수조사")
    if st.button("🚀 전수조사 시작"):
        token = get_naver_token()
        if token:
            st.success("✅ 네이버 인증 성공! 데이터를 불러옵니다.")
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
                        results.append({"상품명": name, "AI 진단": check_trademark(name)})
                    st.dataframe(pd.DataFrame(results), use_container_width=True)
            else:
                st.warning("⚠️ 상품 정보를 가져오지 못했습니다. API 그룹에 '상품'이 추가됐는지 확인하세요.")

elif menu == "🎁 신규 상품 소싱":
    st.header("🎁 AI 시즌 상품 소싱")
    st.info("도매매 API 승인 대기 중입니다.")
