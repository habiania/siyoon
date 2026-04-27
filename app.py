import streamlit as st
import requests
import xml.etree.ElementTree as ET
import google.generativeai as genai

# 1. 인증 정보 (Streamlit Secrets에서 안전하게 로드)
try:
    DOMAEMAE_ID = st.secrets["DOMAEMAE_ID"]
    DOMAEMAE_KEY = st.secrets["DOMAEMAE_KEY"]
    KIPRIS_KEY = st.secrets["KIPRIS_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
    genai.configure(api_key=GEMINI_KEY)
except Exception as e:
    st.error("Secrets 설정이 올바르지 않습니다. 설정을 확인해주세요.")
    st.stop()

# 2. 키프리스 상표권 조회 함수
def check_kipris(word):
    url = "http://plus.kipris.or.kr/openapi/rest/TrademarkSearchService/freeSearch"
    # 상품명 전체가 아닌, 띄어쓰기 기준 첫 단어로 체크 (더 엄격한 검증)
    check_word = word.split()[0] 
    params = {
        "ServiceKey": KIPRIS_KEY,
        "trademarkName": check_word,
        "resultType": "json"
    }
    try:
        res = requests.get(url, params=params).json()
        count = res.get('body', {}).get('items', {}).get('totalCount', 0)
        return int(count) > 0
    except:
        return False

# --- 메인 화면 UI ---
st.set_page_config(page_title="상표권 방어 시스템", layout="wide")
st.title("🛡️ 실전 상표권 방어 & 상품 소싱")

with st.sidebar:
    st.header("🔍 테스트 설정")
    target_keyword = st.text_input("검색어 입력 (예: 기절토퍼)", value="기절토퍼")
    start_btn = st.button("실제 데이터 분석 시작")

if start_btn:
    st.info(f"'{target_keyword}'로 도매매 실시간 데이터를 가져오는 중...")
    
    # 3. 도매매 API 호출 (실제 상품 리스트 가져오기)
    doma_url = "http://openapi.domaemae.com/cgi-bin/domaemall/api/get_item_list.php"
    doma_params = {
        "userid": DOMAEMAE_ID,
        "apikey": DOMAEMAE_KEY,
        "mode": "getItemList",
        "search_word": target_keyword,
        "rows": 10
    }
    
    try:
        response = requests.get(doma_url, params=doma_params)
        root = ET.fromstring(response.text)
        # XML에서 진짜 상품명만 추출
        items = [item.find('item_name').text for item in root.findall('.//item')]
    except Exception as e:
        st.error(f"도매매 API 연결 실패: {e}")
        items = []

    if items:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📦 도매매 검색 결과 (상표권 검증)")
            for item in items:
                is_unsafe = check_kipris(item)
                if is_unsafe:
                    st.error(f"❌ 위험: {item}")
                else:
                    st.success(f"✅ 안전: {item}")
        
        with col2:
            st.subheader("📝 AI 추천 상품명 & 홍보글")
            # 안전한 상품 중 첫 번째로 AI 글쓰기 테스트
            safe_list = [i for i in items if not check_kipris(i)]
            if safe_list:
                model = genai.GenerativeModel('gemini-pro')
                res = model.generate_content(f"상품 '{safe_list[0]}'을 상표권 침해 걱정 없는 일반적인 용어로 재구성하고 홍보글 써줘.")
                st.write(res.text)
            else:
                st.warning("안전한 상품이 없어 AI가 글을 작성하지 않았습니다.")
    else:
        st.warning("검색 결과가 없습니다. 도매매 API 승인 상태나 키워드를 확인하세요.")
