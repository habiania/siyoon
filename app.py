import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

# --- [1. 설정 정보] ---
# 사장님이 새로 발급받은 일반 계정 정보 적용
GEMINI_API_KEY = "AIzaSyDPwqZCgMvsESnP5kg3C-ZDSIW3tt3xSYU" 
DOME_ID = "ryule1122"  # 새 아이디
DOME_KEY = "7f476022a7670ce1f483b470c6b1aef9" # 새 인증키

# 제미나이 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
today_str = datetime.now().strftime("%Y-%m-%d")

st.set_page_config(page_title="Gemini AI 시즌 소싱 마스터", layout="wide")

# --- [2. 핵심 함수: 도매매 수집] ---
def fetch_dome_data(keyword, limit=10):
    # 일반 계정용 표준 API 주소
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
        # 브라우저인 척 접근하기 위한 헤더
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, params=params, headers=headers, timeout=10)
        
        # 글자 깨짐 방지 (EUC-KR 처리)
        try:
            content = res.content.decode('utf-8')
        except UnicodeDecodeError:
            content = res.content.decode('euc-kr', errors='replace')
        
        root = ET.fromstring(content)
        msg_node = root.find(".//message")
        
        # 도매매 서버의 응답 확인
        if msg_node is not None and msg_node.text != "OK":
            st.warning(f"도매매 알림: {msg_node.text}")
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
        st.error(f"연결 오류 발생: {e}")
        return pd.DataFrame()

# --- [3. 핵심 함수: 제미나이 가공] ---
def ai_process(row, margin, fee):
    # 제미나이에게 보내는 가공 요청
    prompt = f"""
    온라인 쇼핑몰 전문가로서 다음 상품을 가공해줘.
    [원본명] {row['원본상품명']} / [원가] {row['공급가']}원 / [오늘날짜] {today_str}
    미션: 
    1. 상표권 위험 단어는 삭제하고, 지금 시즌에 맞는 매력적인 25자 내외 상품명으로 변경.
    2. 수수료 {fee*100}%와 마진 {margin*100}%를 계산해서 끝자리가 900원인 최적가 산출.
    양식: 이름: (이름) / 가격: (숫자)
    """
    try:
        response = model.generate_content(prompt)
        txt = response.text
        # 결과값에서 이름과 가격만 추출
        name = re.search(r"이름:\s*(.*?)\s*/", txt).group(1).strip() if "이름:" in txt else row['원본상품명']
        price_find = re.findall(r'\d+', txt.split("가격:")[1]) if "가격:" in txt else []
        price = int(price_find[0]) if price_find else int(row['공급가'] * 1.3)
        return name, price
    except:
        return row['원본상품명'], int(row['공급가'] * 1.3)

# --- [4. 메인 화면 구성] ---
st.title(f"♊ Gemini AI 시즌 소싱 ({today_str})")
st.sidebar.header("⚙️ 전략 설정")
target_margin = st.sidebar.slider("순마진율 (%)", 5, 50, 25) / 100
market_fee = 0.066 # 기본 수수료 6.6%

search_keyword = st.text_input("소싱 키워드 (예: 양말, 슬리퍼, 캠핑용품)", value="양말")

if st.button(f"🚀 '{search_keyword}' 10개 수집 및 Gemini 가공 시작"):
    with st.spinner("구글 제미나이가 상품을 분석 중입니다..."):
        df = fetch_dome_data(search_keyword, 10)
        
        if not df.empty:
            processed_data = []
            for _, row in df.iterrows():
                new_name, new_price = ai_process(row, target_margin, market_fee)
                profit = new_price - row['공급가'] - (new_price * market_fee)
                processed_data.append({
                    "가공상품명": new_name,
                    "AI추천가": f"{new_price:,}원",
                    "예상순익": f"{int(profit):,}원"
                })
            
            final_result = pd.concat([df, pd.DataFrame(processed_data)], axis=1)
            st.success("✅ 성공적으로 가공되었습니다!")
            st.dataframe(final_result[["상품코드", "원본상품명", "공급가", "가공상품명", "AI추천가", "예상순익"]], use_container_width=True)
            
            st.subheader("🖼️ 상품 썸네일 미리보기")
            cols = st.columns(5)
            for i, row in df.iterrows():
                with cols[i % 5]:
                    if row['이미지']: st.image(row['이미지'], caption=row['상품코드'])
        else:
            st.error("데이터를 가져오지 못했습니다. 도매매 API 센터에서 새 키가 '사용중'인지 확인해 주세요.")
