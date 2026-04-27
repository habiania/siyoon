import streamlit as st
import requests
import xml.etree.ElementTree as ET
import google.generativeai as genai

# 1. 인증 정보 (Secrets 사용 권장하나, 일단 직접 입력 버전으로 통합)
DOMAEMAE_ID = "sns@262783"
DOMAEMAE_KEY = "6a35f4068cfa2de71ee4229d89f5999f"
KIPRIS_KEY = st.secrets.get("KIPRIS_KEY", "LcPZHKFPUbVb=Wz0D4TVEn9zei09FcB3/92w=reAhMU=")
GEMINI_KEY = st.secrets.get("GEMINI_KEY", "")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# 2. 키프리스 상표권 조회 함수
def check_kipris(word):
    url = "http://plus.kipris.or.kr/openapi/rest/TrademarkSearchService/freeSearch"
    check_word = word.split()[0] # 첫 단어 기준 검사
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

# --- UI 구성 (이 부분이 if start_btn 보다 위에 있어야 합니다) ---
st.set_page_config(page_title="상표권 방어 시스템", layout="wide")
st.title("🛡️ 실전 상표권 방어 & 상품 소싱")

with st.sidebar:
    st.header("🔍 테스트 설정")
    target_keyword = st.text_input("검색어 입력", value="기절토퍼")
    # 여기서 버튼을 먼저 정의합니다!
    start_btn = st.button("실제 데이터 분석 시작")

# --- 로직 실행 ---
if start_btn:
    st.info(f"'{target_keyword}' 데이터 연결 시도 중...")
    
    # 도매매 공식 API 호출 주소
    doma_url = "https://openapi.domeggook.com/cgi-bin/domaemall/api/get_item_list.php"
    
    doma_params = {
        "userid": DOMAEMAE_ID,
        "apikey": DOMAEMAE_KEY,
        "mode": "getItemList",
        "search_word": target_keyword,
        "rows": 10
    }
    
    try:
        response = requests.get(doma_url, params=doma_params, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            items = [item.find('item_name').text for item in root.findall('.//item') if item.find('item_name') is not None]
            
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
                    st.subheader("📝 AI 추천 문구")
                    if GEMINI_KEY:
                        safe_list = [i for i in items if not check_kipris(i)]
                        if safe_list:
                            model = genai.GenerativeModel('gemini-pro')
                            res = model.generate_content(f"상품 '{safe_list[0]}'의 안전한 홍보 문구를 써줘.")
                            st.write(res.text)
            else:
                st.warning("검색 결과가 없습니다.")
        else:
            st.error(f"서버 응답 에러: {response.status_code}")
    except Exception as e:
        st.error(f"연결 실패: {e}")
