import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

# --- [1. 설정 정보] ---
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
DOME_KEY = "69e11616807b334323c19d1a80cfd491" 
# 이미지에서 확인된 사장님 정보
DOME_ID_FULL = "sns@262783"
DOME_ID_NUM = "262783"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="Gemini AI 시즌 소싱 마스터", layout="wide")

# --- [2. 핵심 함수: 도매매 수집 (3단계 인증 시도)] ---
def fetch_dome_data(keyword, limit=10):
    # 도매매 API 표준 주소 (가장 안정적인 경로)
    url = "http://openapi.domeggook.com/helper/api/itemList"
    
    # 시도할 아이디 목록 (연동 계정 특성 고려)
    id_list = [DOME_ID_FULL, DOME_ID_NUM, "cooking_4u"] # 이메일 앞자리까지 후보군 추가
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for try_id in id_list:
        params = {
            "ver": "2.0",
            "mode": "getItemList",
            "aid": DOME_KEY,      
            "id": try_id,        
            "market": "dome",     
            "sw": keyword,    
            "sz": limit,      
            "sort": "reg"     
        }
        
        try:
            res = requests.get(url, params=params, headers=headers, timeout=10)
            content = res.content.decode('euc-kr', errors='replace')
            
            # 성공적으로 아이템을 가져온 경우 루프 종료
            if "<item>" in content:
                root = ET.fromstring(content)
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
                
        except Exception:
            continue
            
    return pd.DataFrame()

# --- [3. 핵심 함수: 제미나이 가공] ---
def ai_process(row, margin, fee):
    prompt = f"위탁판매 상품명 '{row['원본상품명']}'(원가:{row['공급가']}원)을 {today_str} 시즌에 맞춰 가공해줘. 상표권 제외, 25자 내외. 가격은 마진{margin*100}%와 수수료{fee*100}% 포함, 끝자리 900원. 형식: 이름: (이름) / 가격: (숫자)"
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

keyword = st.text_input("소싱 키워드 (예: 양말, 슬리퍼, 캠핑)", value="양말")

if st.button(f"🚀 '{keyword}' 분석 시작"):
    with st.spinner("도매매 서버와 통신 중..."):
        df = fetch_dome_data(keyword, 10)
        
        if not df.empty:
            processed = []
            for _, row in df.iterrows():
                n, p = ai_process(row, target_margin, market_fee)
                profit = p - row['공급가'] - (p * market_fee)
                processed.append({"가공명": n, "AI가격": f"{p:,}원", "수익": f"{int(profit):,}원"})
            
            result = pd.concat([df, pd.DataFrame(processed)], axis=1)
            st.success("✅ 연결 및 소싱 성공!")
            st.dataframe(result[["상품코드", "원본상품명", "공급가", "가공명", "AI가격", "수익"]], use_container_width=True)
            
            cols = st.columns(5)
            for i, row in df.iterrows():
                with cols[i % 5]:
                    if row['이미지']: st.image(row['이미지'], caption=row['상품코드'])
        else:
            st.error("데이터를 가져오지 못했습니다. 도매매 API 승인 상태나 IP 제한을 다시 확인해 주세요.")
