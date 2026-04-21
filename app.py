import streamlit as st
import pandas as pd
from openai import OpenAI
import math

# --- [1. 기본 설정 및 보안] ---
# 실제 사용 시 발급받은 API 키를 여기에 입력하세요
OPENAI_KEY = "sk-..." 
KIPRIS_KEY = "인증키를_입력하세요"

client = OpenAI(api_key=OPENAI_KEY)

st.set_page_config(page_title="AI 위탁판매 자동화", layout="wide", initial_sidebar_state="expanded")

# --- [2. 핵심 로직 함수] ---

def ai_optimizer(row, margin_rate, fee_rate):
    """AI가 상품명 가공 및 심리적 최적가 책정"""
    cost = row['공급가']
    original_name = row['원본상품명']
    
    prompt = f"""
    너는 한국 이커머스 최적화 전문가야.
    [데이터] 원본명: {original_name}, 원가: {cost}원, 목표마진: {margin_rate*100}%, 수수료: {fee_rate*100}%
    
    [미션]
    1. 상품명: 브랜드/상표권 단어는 무조건 제거하거나 일반명사로 치환. 클릭을 부르는 키워드를 섞어 25자 내외로 작명.
    2. 가격: 수수료 {fee_rate*100}%와 마진을 감안해 역산한 뒤, 소비자가 '혜자'라고 느낄 심리적 가격(예: 끝자리 900원, 800원)을 숫자만 제안.
    
    [출력형식] 상품명: (이름) / 가격: (숫자)
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        res_text = response.choices[0].message.content
        new_name = res_text.split("상품명:")[1].split("/")[0].strip()
        new_price = int(res_text.split("가격:")[1].strip().replace(",", ""))
        return new_name, new_price
    except:
        # 에러 발생 시 수동 계산 안전장치
        fallback = (int((cost / (1 - margin_rate - fee_rate)) // 1000) * 1000) + 900
        return f"[검토필요] {original_name}", fallback

# --- [3. 모바일용 웹 화면 구성] ---

st.title("📱 AI 대량 등록 제어센터")
st.markdown("---")

# 사이드바: 전략 컨트롤러 (폰에서 조절 가능)
st.sidebar.header("💰 가격 및 수수료 전략")
st_margin = st.sidebar.slider("목표 순마진 (%)", 5, 50, 25) / 100
st_fee = st.sidebar.number_input("마켓 수수료 (%)", value=6.6) / 100

# 메인 화면: 데이터 수집 (샘플 데이터)
st.subheader("📦 수집된 상품 리스트")
sample_data = {
    "상품코드": ["DOM-001", "DOM-002", "DOM-003"],
    "원본상품명": ["나이키 스타일 런닝화", "아디다스 캠핑용 폴딩체어", "정품 가죽 남성 벨트"],
    "공급가": [22000, 35000, 11000]
}
df = pd.DataFrame(sample_data)
st.dataframe(df, use_container_width=True)

# 실행 버튼
if st.button("🚀 AI 지능형 대량 가공 시작", use_container_width=True):
    if "sk-" not in OPENAI_KEY:
        st.error("OpenAI API 키를 먼저 설정해주세요!")
    else:
        with st.spinner("AI가 수수료를 계산하고 상표권을 피하는 중..."):
            processed_list = []
            for _, row in df.iterrows():
                new_name, new_price = ai_optimizer(row, st_margin, st_fee)
                
                # 순수익 계산기
                real_profit = new_price - row['공급가'] - (new_price * st_fee)
                
                processed_list.append({
                    "가공 상품명": new_name,
                    "AI 추천가": f"{new_price:,}원",
                    "예상 순익": f"{int(real_profit):,}원"
                })
            
            # 결과 표시
            res_df = pd.concat([df, pd.DataFrame(processed_list)], axis=1)
            st.success("✅ 가공이 완료되었습니다!")
            st.dataframe(res_df, use_container_width=True)

# 하단 정보
st.caption("작동 순서: 도매처 데이터 로드 ➔ AI 상표권 필터링 ➔ 수수료 기반 가격 책정 ➔ 등록 대기")