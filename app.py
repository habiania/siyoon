import streamlit as st
import pandas as pd
import requests
import google.generativeai as genai
import io

# 1. 인증 정보 설정 (Secrets 사용)
KIPRIS_KEY = st.secrets.get("KIPRIS_KEY", "LcPZHKFPUbVb=Wz0D4TVEn9zei09FcB3/92w=reAhMU=")
GEMINI_KEY = st.secrets.get("GEMINI_KEY", "")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# 2. 상표권 조회 함수 (핵심 단어 추출 검사)
def check_kipris(word):
    if not word or pd.isna(word):
        return False
    
    url = "http://plus.kipris.or.kr/openapi/rest/TrademarkSearchService/freeSearch"
    
    # 상품명에서 첫 번째 단어(보통 브랜드나 핵심키워드)를 추출
    check_word = str(word).split()[0]
    
    params = {
        "ServiceKey": KIPRIS_KEY,
        "trademarkName": check_word,
        "resultType": "json"
    }
    
    try:
        res = requests.get(url, params=params, timeout=5).json()
        count = res.get('body', {}).get('items', {}).get('totalCount', 0)
        return int(count) > 0
    except:
        return False

# --- UI 구성 ---
st.set_page_config(page_title="상표권 엑셀 검수기", layout="wide")
st.title("🛡️ 상표권 전수 조사 & 엑셀 검수 시스템")
st.info("도매매에서 다운로드한 상품 DB 엑셀 파일을 업로드하세요.")

# 파일 업로드
uploaded_file = st.file_uploader("엑셀 또는 CSV 파일 선택", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    # 데이터 로드
    try:
        if uploaded_file.name.endswith(('xlsx', 'xls')):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)
        
        st.success(f"✅ {len(df)}개의 상품 데이터를 불러왔습니다.")
        
        # 컬럼 선택 (도매매 엑셀은 보통 '상품명' 컬럼 사용)
        col_list = df.columns.tolist()
        target_col = st.selectbox("상품명이 들어있는 컬럼을 선택하세요", col_list, 
                                  index=col_list.index('상품명') if '상품명' in col_list else 0)

        if st.button("🚀 상표권 일괄 검사 시작"):
            st.divider()
            results = []
            
            # 진행 바
            progress_text = "상표권을 조회 중입니다. 잠시만 기다려 주세요..."
            my_bar = st.progress(0, text=progress_text)
            
            # 테스트를 위해 상위 30개만 먼저 진행 (필요시 숫자 변경 가능)
            limit = min(len(df), 30) 
            
            for i in range(limit):
                item_name = df.iloc[i][target_col]
                is_unsafe = check_kipris(item_name)
                
                status = "❌ 위험 (상표권 있음)" if is_unsafe else "✅ 안전"
                results.append({"상품명": item_name, "검수 결과": status})
                
                # 진행률 업데이트
                my_bar.progress((i + 1) / limit, text=f"{i+1}/{limit} 분석 중...")

            # 결과 표 출력
            res_df = pd.DataFrame(results)
            
            # 결과 시각화
            col_res, col_ai = st.columns([1, 1])
            
            with col_res:
                st.subheader("📋 검수 결과 리스트")
                st.dataframe(res_df, use_container_width=True)

            with col_ai:
                st.subheader("📝 AI 안전 문구 제안")
                # 안전한 상품 하나 골라서 AI 문구 생성 테스트
                safe_items = res_df[res_df['검수 결과'] == "✅ 안전"]
                if not safe_items.empty and GEMINI_KEY:
                    sample_name = safe_items.iloc[0]['상품명']
                    st.write(f"**대상 상품:** {sample_name}")
                    model = genai.GenerativeModel('gemini-pro')
                    prompt = f"상품명 '{sample_name}'을 상표권 침해 없는 안전하고 매력적인 판매 제목으로 바꾸고 짧은 홍보글 써줘."
                    response = model.generate_content(prompt)
                    st.write(response.text)
                else:
                    st.write("안전한 상품이 없거나 AI 키가 설정되지 않았습니다.")
                    
    except Exception as e:
        st.error(f"파일을 읽는 중 에러가 발생했습니다: {e}")
