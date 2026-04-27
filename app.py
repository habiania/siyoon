import requests
import json

# 공유해주신 정보 설정
USER_ID = "sns@262783"
API_KEY = "6a35f4068cfa2de71ee4229d89f5999f"

def search_domaemae_items(keyword):
    # 도매매 API 호출 주소 (실제 명세서상의 엔드포인트 확인 필요)
    # 아래는 일반적인 도매매 오픈 API 호출 방식의 예시입니다.
    url = "https://openapi.domaemae.com/endpoint" # 실제 승인된 API URL로 수정 필요
    
    params = {
        "userid": USER_ID,
        "apikey": API_KEY,
        "mode": "getItemList",  # 상품 리스트 가져오기 모드
        "search_word": keyword, # 검색어
        "rows": 10              # 가져올 개수
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # 에러 발생 시 예외 처리
        
        # 도매매 API는 보통 XML이나 JSON으로 응답합니다.
        # JSON 응답이라고 가정할 때:
        data = response.json()
        return data
    
    except Exception as e:
        print(f"에러 발생: {e}")
        return None

# 실행 테스트: '캠핑' 키워드로 검색
if __name__ == "__main__":
    result = search_domaemae_items("캠핑")
    if result:
        print(json.dumps(result, indent=4, ensure_ascii=False))
    else:
        print("데이터를 가져오지 못했습니다. API 주소나 권한을 확인해 보세요.")
