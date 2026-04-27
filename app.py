# 3. 도매매 API 호출 부분 수정
if start_btn:
    st.info(f"'{target_keyword}' 데이터 연결 시도 중...")
    
    # 도매매/도매꾹 Open API 공식 호출 주소 (PHP 경로 포함)
    doma_url = "https://openapi.domeggook.com/cgi-bin/domaemall/api/get_item_list.php"
    
    doma_params = {
        "userid": "sns@262783",
        "apikey": "6a35f4068cfa2de71ee4229d89f5999f",
        "mode": "getItemList",
        "search_word": target_keyword,
        "rows": 10
    }
    
    try:
        # 1. timeout을 15초로 넉넉히 설정
        # 2. https 호출 시 발생할 수 있는 SSL 인증서 문제를 위해 verify=True 설정
        response = requests.get(doma_url, params=doma_params, timeout=15)
        
        if response.status_code == 200:
            # 성공 시 데이터 처리
            root = ET.fromstring(response.text)
            items = [item.find('item_name').text for item in root.findall('.//item') if item.find('item_name') is not None]
        else:
            st.error(f"서버 응답 에러 (코드: {response.status_code})")
            items = []
    except Exception as e:
        st.error(f"연결 실패: {e}")
        items = []
