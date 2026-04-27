import streamlit as st
import requests
import google.generativeai as genai

# 사이트 설정
st.set_page_config(page_title="AI 상품 소싱 & 상표권 검증", layout="wide")
st.title("🚀 AI 자동화 상품 소싱 시스템")

# 설정 정보 (Streamlit Secrets에서 불러오기)
# 직접 입력하거나 배포 사이트 설정에서 관리 가능합니다.
DOMAEMAE_ID = st.secrets.get("DOMAEMAE_ID", "sns@262783")
DOMAEMAE_KEY = st.secrets.get("DOMAEMAE_KEY", "6a35f4068cfa2de71ee4229d89f5999f")
KIPRIS_KEY = st.secrets.get("KIPRIS_KEY", "LcPZHKFPUbVb=Wz0D4TVEn9zei09FcB3/92w=reAhMU=")
GEMINI_KEY = st.secrets.get("GEMINI_KEY", "")

# 1. 도매매 검색 함수
def get_domaemae_items(keyword):
    url = "http://openapi.domaemae.com/cgi-bin/domaemall/api/get_item_list.php"
    params = {
        "userid": DOMAEMAE_ID,
        "apikey": DOMAEMAE_KEY,
        "mode": "getItemList",
        "search_word": keyword,
        "rows": 10
    }
    return requests.get(url, params=params).text

# 2. 키프리스 검증 함수
def check_kipris(word):
    url = "http://plus.kipris.or.kr/openapi/rest/TrademarkSearchService/freeSearch"
    params = {"ServiceKey": KIPRIS_KEY, "trademarkName": word, "resultType": "json"}
    try:
        res = requests.get(url, params=params).json()
        count = res.get('body', {}).get('items', {}).get('totalCount', 0)
        return int(count) > 0
    except: return False

# --- 사이드바 및 UI ---
with st.sidebar:
    st.header("🔍 검색 설정")
    target_keyword = st.text_input("소싱할 키워드", value="육아용품")
    start_btn = st.button("자동화 프로세스 시작")

if start_btn:
    st.info(f"'{target_keyword}' 상품을 분석 중입니다...")
    
    # [가상 데이터 처리 - 실제 XML 파싱 로직 추가 필요]
    sample_items = ["하기스 기저귀", "디즈니 물티슈", "일반형 턱받이"] 
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 도매매 소싱 리스트")
        for item in sample_items:
            is_reg = check_kipris(item)
            if is_reg:
                st.error(f"❌ {item} (상표권 주의)")
            else:
                st.success(f"✅ {item} (안전)")
                
    with col2:
        st.subheader("📝 AI 홍보 문구")
        if GEMINI_KEY:
            # AI 생성 로직 실행
            st.write("AI가 글을 작성하고 있습니다...")
        else:
            st.warning("Gemini API Key를 등록하면 AI 글쓰기가 활성화됩니다.")
