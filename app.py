import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from datetime import datetime
import re

# --- [1. 설정 정보] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
DOME_ID = "ryule1122"  # 새 일반계정 아이디
DOME_KEY = "7f476022a7670ce1f483b470c6b1aef9" # 새 일반계정 인증키

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="Gemini AI 시즌 소싱 마스터", layout="wide")

# --- [2. 핵심 함수: 도매매 수집 (강제 텍스트 추출 방식)] ---
def fetch_dome_data(keyword, limit=10):
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
        # 헤더를 넣어 안정적인 연결 확보
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, params=params, headers=headers, timeout=15)
        
        # 글자 깨짐 무시하고 읽기 (도매매 특유의 인코딩 방어)
        content = res.content.decode('euc-kr', errors='ignore')
        
        # [핵심] XML 해석기가 에러나도 상관없게 정규표현식으로 텍스트만 뽑아냄
        items = []
        blocks = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
        
        for b in blocks:
            try:
                # 각 항목에서 필요한 정보만 쏙쏙 추출
                no = re.search(r'<no>(.*?)</no>', b).group(1)
                title = re.search(r'<title>(.*?)</title>', b).group(1)
                price = re.search(r'<price>(.*?)</price>', b).group(1)
                img = re.search(r'<img>(.*?)</img>', b).group(1)
                
                items.append({
                    "상품코드": no,
                    "원본상품명": title,
                    "공급가": int(price),
                    "이미지": img
                })
            except: continue
                
        return pd.DataFrame(items)
    except Exception as e:
        st.error(f"📡 서버 응답 처리 중 문제 발생: {e}")
        return pd.DataFrame()

# --- [3. 핵심 함수: 제미나이 가공] ---
def ai_process(row, margin, fee):
    prompt = f"상품 '{row['원본상품명']}'(원가:{row['공급가']}원)을 {today_str} 시즌에 맞게 작명해줘. 25자 내외. 가격은 마진{margin*100}%와 수수료{fee*100}% 포함해서 끝자리 900원 단위로. 형식: 이름: (이름) / 가격: (숫자)"
    try:
        response = model.generate_content(prompt)
        txt = response.text
        name = re.search(r"이름:\s*(.*?)\s*/", txt).group(1).strip() if "이름:" in txt else row['원본상품명']
        price = re.search(r"가격:\s*([\d,]+)", txt).group(1).replace(",", "") if "가격:" in txt else str(int(row['공급가']*1.4))
        return name, int(price)
    except:
        return f"[시즌추천] {row['원본상품명'][:15]}", int(row['공급가'] * 1.4)

# --- [4. 메인 화면 구성] ---
st.title(f"♊ Gemini AI 시즌 소싱 ({today_str})")
st.markdown("---")

st.sidebar.header("⚙️ 전략 설정")
target_margin = st.sidebar.slider("순마진율 (%)", 5, 50, 25) / 100
market_fee = 0.066 

keyword = st.text_input("소싱 키워드 (예: 양말, 슬리퍼, 캠핑)", value="양말")

if st.button(f"🚀 '{keyword}' 분석 시작"):
    with st.spinner("도매매 서버에서 데이터를 가져오고 있습니다..."):
        df = fetch_dome_data(keyword, 10)
        
        if not df.empty:
            processed = []
            for _, row in df.iterrows():
                n, p = ai_process(row, target_margin, market_fee)
                profit = p - row['공급가'] - (p * market_fee)
                processed.append({"가공명": n, "AI가격": f"{p:,}원", "수익": f"{int(profit):,}원"})
            
            result = pd.concat([df, pd.DataFrame(processed)], axis=1)
            st.success("✅ 소싱 성공! 결과를 확인하세요.")
            st.dataframe(result[["상품코드", "원본상품명", "공급가", "가공명", "AI가격", "수익"]], use_container_width=True)
            
            cols = st.columns(5)
            for i, row in df.iterrows():
                with cols[i % 5]:
                    if row['이미지']: st.image(row['이미지'], caption=row['상품코드'])
        else:
            st.error("데이터를 가져오지 못했습니다. 도매매 API 승인 상태나 IP 제한을 다시 확인해 주세요.")
                    if row['이미지']: st.image(row['이미지'], caption=row['상품코드'])
