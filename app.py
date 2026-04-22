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
DOME_ID = "ryule1122"  
DOME_KEY = "7f476022a7670ce1f483b470c6b1aef9" 
NAVER_CLIENT_ID = "1mrpP8IsCpfwnfvDfci2up"
NAVER_CLIENT_SECRET = "$2a$04$x1.6V7Jjy9AbgkSHqK4wle"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="모던마켓2024 통합 관리 센터", layout="wide")

# --- [2. 핵심 함수: 네이버 인증 토큰 (네이버 가이드 정석 버전)] ---
def get_naver_token():
    timestamp = str(int(time.time() * 1000))
    # [수정] 네이버 API는 ID와 Timestamp를 조합한 뒤 Secret으로 서명(Signature)을 만듭니다.
    password = f"{NAVER_CLIENT_ID}_{timestamp}"
    
    # HMAC-SHA256 암호화 로직
    hashed = hmac.new(
        NAVER_CLIENT_SECRET.encode('utf-8'), 
        password.encode('utf-8'), 
        hashlib.sha256
    ).digest()
    
    signature = base64.b64encode(hashed).decode('utf-8')
    
    url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    
    # [수정] 네이버는 파라미터 형식을 아주 까다롭게 봅니다.
    data = {
        "client_id": NAVER_CLIENT_ID,
        "timestamp": timestamp,
        "grant_type": "client_credentials",
        "client_secret_sign": signature,
        "type": "SELF"
    }
    
    try:
        # 헤더를 비우고 순수하게 데이터만 전송
        res = requests.post(url, data=data)
        res_data = res.json()
        
        if "access_token" in res_data:
            return res_data.get("access_token")
        else:
            # 실패 시 네이버가 보낸 실제 에러 내용을 확인합니다.
            st.error(f"❌ 네이버 응답: {res_data.get('message', '인증 데이터 불일치')}")
            if res_data.get('invalid_params'):
                st.warning(f"상세 원인: {res_data.get('invalid_params')}")
            return None
    except Exception as e:
        st.error(f"📡 네트워크 오류: {e}")
        return None

# --- [3. 핵심 함수: AI 상표권 검사] ---
def check_trademark(name):
    prompt = f"상품명 '{name}'에서 상표권 위반 의심 단어를 찾아줘. 위험하면 [위험], 안전하면 [안전]이라고 쓰고 이유를 한 줄 요약해줘."
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "검사 실패"

# --- [4. 메인 화면 구성] ---
st.sidebar.title("🚀 모던마켓2024")
menu = st.sidebar.radio("작업 선택", ["🛡️ 상표권 전수조사", "🎁 신규 상품 소싱"])

if menu == "🛡️ 상표권 전수조사":
    st.header("🛡️ 내 스토어 상표권 방패")
    
    if st.button("🔍 전수조사 시작"):
        with st.spinner("네이버 서버와 암호화 통신 중..."):
            token = get_naver_token()
            if token:
                st.success("✅ 인증 성공! 상품 데이터를 가져옵니다.")
                url = "https://api.commerce.naver.com/external/v1/products/search"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                # 우선 최근 20개만 테스트
                payload = {"page": 1, "size": 20}
                
                res = requests.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    products = res.json().get("contents", [])
                    if not products:
                        st.info("스토어에 등록된 상품이 없습니다.")
                    else:
                        results = []
                        for p in products:
                            p_name = p.get("name")
                            p_id = p.get("originProductNo")
                            p_status = check_trademark(p_name)
                            results.append({"상품번호": p_id, "상품명": p_name, "AI 진단": p_status})
                        
                        st.dataframe(pd.DataFrame(results), use_container_width=True)
                else:
                    st.warning("상품 정보를 가져오지 못했습니다. API 권한 설정을 확인하세요.")

elif menu == "🎁 신규 상품 소싱":
    st.header("🎁 AI 시즌 상품 소싱")
    st.info("도매매 API 승인 대기 중입니다.")
