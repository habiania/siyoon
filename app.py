import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# --- [설정] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
DOME_ID = "sns@262783"
DOME_KEY = "69e11616807b334323c19d1a80cfd491"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("⚙️ 도매매 연결 정밀 진단")

if st.button("🔍 연결 상태 테스트 시작"):
    url = "http://openapi.domeggook.com/helper/api/itemList"
    params = {
        "ver": "2.0",
        "mode": "getItemList",
        "aid": DOME_KEY,
        "market": "dome",
        "sw": "양말",
        "sz": 1
    }
    
    try:
        res = requests.get(url, params=params)
        # 글자 깨짐 방지 처리하여 읽기
        content = res.content.decode('euc-kr', errors='replace')
        
        st.code(content, language='xml') # 서버 응답 원본을 화면에 보여줍니다.
        
        if "<message>OK</message>" in content:
            st.success("✅ 연결 성공! 이제 데이터를 정상적으로 가져올 수 있습니다.")
        else:
            st.error("❌ 도매매 서버에서 거부됨. 위 응답 메시지 내용을 확인하세요.")
            
    except Exception as e:
        st.error(f"📡 통신 자체가 안 됨: {e}")
