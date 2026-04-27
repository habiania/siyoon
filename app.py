# 3. 도매매 API 호출 주소 최종 수정
if start_btn:
    st.info(f"'{target_keyword}' 데이터 연결 시도 중...")
    
    # 404 에러를 피하기 위한 최신 도매매 API 엔드포인트
    # 기존 cgi-bin 경로 대신 이 주소를 많이 사용합니다.
    doma_url = "https://openapi.domeggook.com/endpoint" 
    
    doma_params = {
        "userid": DOMAEMAE_ID,
        "apikey": DOMAEMAE_KEY,
        "mode": "getItemList",
        "search_word": target_keyword,
        "rows": 10,
        "xml" : "1" # XML 데이터를 명시적으로 요청
    }
    
    try:
        response = requests.get(doma_url, params=doma_params, timeout=15)
        
        # 만약 위 주소도 404가 뜨면 아래 주소로 한 번 더 시도하게 로직 보강
        if response.status_code == 404:
            alt_url = "https://openapi.domaemae.com/endpoint"
            response = requests.get(alt_url, params=doma_params, timeout=15)

        if response.status_code == 200:
            # 성공 시 로직 (기존과 동일)
            root = ET.fromstring(response.text)
            items = [item.find('item_name').text for item in root.findall('.//item') if item.find('item_name') is not None]
            # ... (이후 출력 로직)
        else:
            st.error(f"서버 응답 에러 (코드: {response.status_code})")
            st.info("도매매 API 관리 페이지에서 'API 주소'를 다시 확인해야 할 수도 있습니다.")
