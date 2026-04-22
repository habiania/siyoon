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

st.set_page_config(page_title="모던마켓2024 통합 센터", layout="wide")

# --- [2. 핵심 함수: 네이버 인증 토큰 (정밀 수정 버전)] ---
def get_naver_token():
    timestamp = str(int(time.time() * 1000))
    # Secret Key를 사용하여 Signature 생성 (네이버 표준 가이드 준수)
    password = f"{NAVER_CLIENT_ID}_{timestamp}"
    hashed = hmac.new(NAVER_CLIENT_SECRET.encode('utf-8'), password.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(hashed).decode('utf-8')
    
    url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    
    # [수정] 네이버 API는 헤더가 아닌 '데이터 바디' 형식을 매우 엄격하게 따집니다.
    params = {
        "client_id": NAVER_CLIENT_ID,
        "timestamp": timestamp,
        "grant_type": "client_credentials",
        "client_secret_sign": signature,
        "type": "SELF"
    }
    
    try:
        res = requests.post(url, data=params) # json이 아닌 data로 전송
        res_data = res.json()
        if "access_token" in res_data:
            return res_data.get("access_token")
        else:
            st.error(f"❌ 네이버 메시지: {res_data.get('message', '알 수 없는 인증 오류')}")
            return None
    except Exception as e:
        st.error(f"📡 네트워크 오류: {e}")
        return None

# --- [3. 핵심 함수: AI 상표권 검사] ---
def check_trademark(name):
    prompt = f"상품명 '{name}'에서 상표권 위반(유명 브랜드 사칭, 지재권 침해) 단어가 있는지 검사해줘. 위험하면 [위험], 안전하면 [안전]이라고 쓰고 이유를 한 줄로 요약해줘."
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "검사 실패"

# --- [4. 메인 화면 구성] ---
st.sidebar.title("🚀 모던마켓2024")
menu = st.sidebar.radio("작업 선택", ["🛡️ 상표권 전수조사", "🎁 신규 상품 소싱"])

if menu == "🛡️ 상표권 전수조사":
    st.header("🛡️ 내 스토어 상표권 방패")
    
    if st.button("🔍 내 스토어 상품 검사 시작"):
        with st.spinner("네이버 서버 인증 중..."):
            token = get_naver_token()
            if token:
                st.success("✅ 네이버 인증 성공! 상품 리스트를 분석합니다.")
                # 상품 목록 조회 API 호출
                url = "https://api.commerce.naver.com/external/v1/products/search"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                data = {"page": 1, "size": 30} # 우선 30개씩
                
                res = requests.post(url, headers=headers, json=data)
                if res.status_code == 200:
                    products = res.json().get("contents", [])
                    if not products:
                        st.info("조회된 상품이 없습니다.")
                    else:
                        results = []
                        for p in products:
                            p_name = p.get("name")
                            p_id = p.get("originProductNo")
                            p_status = check_trademark(p_name)
                            results.append({"상품번호": p_id, "상품명": p_name, "AI 진단": p_status})
                        
                        df = pd.DataFrame(results)
                        st.dataframe(df, use_container_width=True)
                else:
                    st.warning("⚠️ 상품 권한이 승인되지 않았거나 조회할 수 없습니다. (API 그룹 확인 필요)")
            else:
                st.error("🔑 토큰 발급에 실패했습니다. Client Secret 복사 시 공백이 포함되었는지 확인하세요.")

elif menu == "🎁 신규 상품 소싱":
    st.header("🎁 AI 시즌 상품 소싱")
    st.info("도매매 API 승인 완료 후 사용 가능합니다.")
