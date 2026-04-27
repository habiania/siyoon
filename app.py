import requests
import xml.etree.ElementTree as ET
import google.generativeai as genai

# 1. 인증 정보 설정
DOMAEMAE_CONF = {"id": "sns@262783", "key": "6a35f4068cfa2de71ee4229d89f5999f"}
KIPRIS_KEY = "LcPZHKFPUbVb=Wz0D4TVEn9zei09FcB3/92w=reAhMU="
# Gemini 키가 있다면 여기에 넣으세요
genai.configure(api_key="YOUR_GEMINI_API_KEY")

def get_domaemae_items(keyword):
    """도매매에서 상품 리스트 가져오기"""
    url = "http://openapi.domaemae.com/cgi-bin/domaemall/api/get_item_list.php"
    params = {
        "userid": DOMAEMAE_CONF["id"],
        "apikey": DOMAEMAE_CONF["key"],
        "mode": "getItemList",
        "search_word": keyword,
        "rows": 5  # 테스트용으로 5개만
    }
    response = requests.get(url, params=params)
    # 도매매는 XML 응답이 기본인 경우가 많으므로 파싱이 필요할 수 있습니다.
    return response.text

def check_kipris_trademark(word):
    """키프리스 상표권 조회 (단어 단위)"""
    url = "http://plus.kipris.or.kr/openapi/rest/TrademarkSearchService/freeSearch"
    params = {
        "ServiceKey": KIPRIS_KEY,
        "trademarkName": word,
        "resultType": "json"
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        # 검색 결과가 있으면(등록된 상표가 있으면) True 반환
        count = data.get('body', {}).get('items', {}).get('totalCount', 0)
        return int(count) > 0
    except:
        return False

def run_automation():
    # 1. 도매매 상품 소싱
    target_keyword = "육아용품" # 원하는 카테고리로 변경 가능
    print(f"1. 도매매에서 '{target_keyword}' 검색 중...")
    items_xml = get_domaemae_items(target_keyword)
    
    # [참고] 여기서는 간단히 로직만 설명합니다. 
    # 실제로는 items_xml에서 상품명(item_name)을 추출하는 과정이 필요합니다.
    sample_items = ["하기스 기저귀", "무명의 턱받이", "삼성 베이비케어"] 

    print("\n2. 상표권 검증 및 AI 문구 생성 시작...")
    for item in sample_items:
        # 2. 키프리스 상표권 검증
        is_registered = check_kipris_trademark(item)
        
        if is_registered:
            print(f"⚠️ [{item}] - 상표권 등록 확인됨 (주의 필요)")
        else:
            print(f"✅ [{item}] - 등록 상표 없음 (진행 가능)")
            
            # 3. AI로 홍보 문구 생성 (Gemini 키가 있을 때만 작동)
            # model = genai.GenerativeModel('gemini-pro')
            # prompt = f"상품명 '{item}'에 대한 네이버 블로그 판매 홍보글을 작성해줘."
            # response = model.generate_content(prompt)
            # print(f"📝 AI 생성글: {response.text[:50]}...")

    print("\n전체 공정 완료!")

if __name__ == "__main__":
    run_automation()
