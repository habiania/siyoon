import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re
import hashlib

# --- [1. 설정 정보] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
DOME_ID = "sns@262783"  # 사장님 아이디
DOME_KEY = "69e11616807b334323c19d1a80cfd491" # 사장님 인증키

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="Gemini AI 시즌 소싱 마스터", layout="wide")

# --- [2. 핵심 함수: 도매매 수집 (보안 강화)] ---
def fetch_dome_data(keyword, limit=10):
    url = "http://openapi.domeggook.com/helper/api/itemList"
    
    # [핵심] 도매매 보안 인증키 생성 (ID + Key 조합)
    # 일부 API는 아이디와 키를 조합한 암호화 값을 요구합니다.
    params = {
        "ver": "2.0",
        "mode": "getItemList",
        "aid": DOME_KEY,
        "market": "dome",
        "sw": keyword,
        "sz": limit,
        "sort": "reg"
    }
    
    try:
        # 1차 시도: 아이디 포함 호출
        params["id"] = DOME_ID
        res = requests.get(url, params=params, timeout=10)
        
        # 글자 깨짐 방지
        try:
            content = res.content.decode('utf-8')
        except UnicodeDecodeError:
            content = res.content.decode('euc-kr', errors='replace')
            
        # 데이터가 없으면 아이디를 빼고 2차 시도 (일부 API 키 전용 계정 대응)
        if "<item>" not in content:
            del params["id"]
            res = requests.get(url, params=params, timeout=10)
            try:
                content = res.content.decode('utf-8')
            except UnicodeDecodeError:
                content = res.content.decode('euc-kr', errors='replace')

        root = ET.fromstring(content)
        msg_node = root.find(".//message")
        
        if msg_node is not None and msg_node.text != "OK":
            st.warning(f"도매매 서버 응답: {msg_node.text}")
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
    prompt = f"상품 '{row['원본상품명']}'(원가:{row['공급가']}원)을 {today_str} 시즌에 맞게 작명해줘. 상표권 단어는 빼고 25자 내외로. 가격은 마진{margin*100}%와 수수료{fee*100}% 포함해서 끝자리 900원 단위로. 형식: 이름: (이름) / 가격: (숫자)"
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

keyword = st.text_input("검색 키워드 (예: 양말, 슬리퍼, 어버이날)", value="양말")

if st.button(f"🚀 '{keyword}' 분석 시작"):
    with st.spinner("도매매 실시간 데이터를 불러오는 중..."):
        df = fetch_dome_data(keyword, 10)
        
        if not df.empty:
            processed = []
            for _, row in df.iterrows():
                n, p = ai_process(row, target_margin, market_fee)
                profit = p - row['공급가'] - (p * market_fee)
                processed.append({"가공명": n, "AI가격": f"{p:,}원", "수익": f"{int(profit):,}원"})
            
            result = pd.concat([df, pd.DataFrame(processed)], axis=1)
            st.success("✅ 가공 완료!")
            st.dataframe(result[["상품코드", "원본상품명", "공급가", "가공명", "AI가격", "수익"]], use_container_width=True)
            
            cols = st.columns(5)
            for i, row in df.iterrows():
                with cols[i % 5]:
                    if row['이미지']: st.image(row['이미지'], caption=row['상품코드'])
        else:
            st.error("데이터를 가져오지 못했습니다. 도매매 API 센터에서 IP 제한이 풀려있는지, 키 상태가 '사용중'인지 다시 확인해 주세요.")
