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

# --- [1. 모든 설정 정보 통합] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
# 도매매 정보
DOME_ID = "ryule1122"  
DOME_KEY = "7f476022a7670ce1f483b470c6b1aef9" 
# 네이버 정보
NAVER_CLIENT_ID = "1mrpP8IsCpfwnfvDfci2up"
NAVER_CLIENT_SECRET = "$2a$04$x1.6V7Jjy9AbgkSHqK4wle"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="모던마켓2024 통합 관리 센터", layout="wide")

# --- [2. 핵심 함수: 네이버 인증 토큰] ---
def get_naver_token():
    timestamp = str(int(time.time() * 1000))
    password = f"{NAVER_CLIENT_ID}_{timestamp}"
    hashed = hmac.new(NAVER_CLIENT_SECRET.encode('utf-8'), password.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(hashed).decode('utf-8')
    url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    data = {"client_id": NAVER_CLIENT_ID, "timestamp": timestamp, "grant_type": "client_credentials", "client_secret_sign": signature, "type": "SELF"}
    res = requests.post(url, data=data)
    return res.json().get("access_token")

# --- [3. 핵심 함수: 도매매 수집] ---
def fetch_dome_data(keyword, limit=10):
    url = "http://openapi.domeggook.com/helper/api/itemList"
    params = {"ver": "2.0", "mode": "getItemList", "aid": DOME_KEY, "id": DOME_ID, "market": "dome", "sw": keyword, "sz": limit, "sort": "reg"}
    try:
        res = requests.get(url, params=params, timeout=10)
        content = res.content.decode('euc-kr', errors='ignore')
        items = []
        blocks = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
        for b in blocks:
            try:
                items.append({
                    "상품코드": re.search(r'<no>(.*?)</no>', b).group(1),
                    "원본상품명": re.search(r'<title>(.*?)</title>', b).group(1),
                    "공급가": int(re.search(r'<price>(.*?)</price>', b).group(1)),
                    "이미지": re.search(r'<img>(.*?)</img>', b).group(1)
                })
            except: continue
        return pd.DataFrame(items)
    except: return pd.DataFrame()

# --- [4. 사이드바 메뉴 구성] ---
st.sidebar.title("🚀 모던마켓2024 본부")
menu = st.sidebar.radio("원하시는 작업을 선택하세요", ["🎁 AI 시즌 상품 소싱", "🛡️ 상표권 위험 검사", "📈 매출 분석 (준비중)"])

# --- [메뉴 1: 상품 소싱] ---
if menu == "🎁 AI 시즌 상품 소싱":
    st.header(f" Gemini AI 시즌 소싱 ({today_str})")
    keyword = st.text_input("소싱 키워드 입력", value="양말")
    if st.button("🚀 분석 시작"):
        df = fetch_dome_data(keyword, 10)
        if not df.empty:
            st.success("도매매 연결 성공!")
            st.dataframe(df[["상품코드", "원본상품명", "공급가"]]) # 가공 로직 생략(공간상)
        else:
            st.error("데이터를 가져오지 못했습니다. 도매매 승인을 확인해주세요.")

# --- [메뉴 2: 상표권 검사] ---
elif menu == "🛡️ 상표권 위험 검사":
    st.header("🛡️ 내 스토어 상표권 방패")
    st.write("네이버 스토어에 등록된 상품의 상표권 위반 여부를 AI가 전수조사합니다.")
    
    if st.button("🔍 내 스토어 상품 불러오기"):
        with st.spinner("네이버 서버와 연결 중..."):
            token = get_naver_token()
            if token:
                # 여기에 상품 조회 API 호출 및 AI 검사 로직이 들어갑니다
                st.info("성공적으로 연결되었습니다! 곧 리스트를 분석합니다.")
                # (상세 분석 코드는 지면상 생략, 연결 확인용)
            else:
                st.error("네이버 API 연결 실패! ID/Secret 혹은 IP 설정을 확인하세요.")

st.sidebar.markdown("---")
st.sidebar.write(f"최종 업데이트: {today_str}")
