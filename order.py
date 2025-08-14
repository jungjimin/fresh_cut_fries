from flask import Flask, request, jsonify, redirect, render_template, session
import requests
import datetime
import random
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.secret_key = "fresh_cut_fries"
Bootstrap(app)  # Flask-Bootstrap 초기화

API_URL = "https://devpgapi.easypay.co.kr/api/ep9/trades/webpay"
APPROVAL_URL = "https://devpgapi.easypay.co.kr/api/ep9/trades/approval"

def generate_shop_transaction_id():
    """ 고유한 shopTransactionId 생성 """
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")  # 현재 일시 (14자리)
    random_number = str(random.randint(0, 999999)).zfill(6)  # 6자리 랜덤 숫자
    return f"fresh{now}{random_number}"  # 예: fresh20250219153045123456

def generate_approval_req_date():
    """ 승인 요청 날짜 (YYYYMMDD) 생성 """
    return datetime.datetime.now().strftime("%Y%m%d")  # 오늘 날짜 (8자리)

def process_transaction(data):
    """ 거래 요청을 보내고 authPageUrl을 받는 함수 """
    response = requests.post(API_URL, json=data)
    response_json = response.json()
    authorization_url = response_json.get("authPageUrl")
    if authorization_url:
        return authorization_url  # URL 반환하여 리디렉션 수행
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        mall_id = request.form.get('mallId', "T0001997")
        session['mallId'] = mall_id  # 세션에 저장

        data = {
            "mallId": mall_id,
            "payMethodTypeCode": request.form.get('payMethodTypeCode', "22"),
            "currency": request.form.get('currency', "00"),
            "amount": int(request.form.get('amount', 51004)),
            "clientTypeCode": request.form.get('clientTypeCode', "00"),
            "returnUrl": request.form.get('returnUrl', "http://192.168.15.89:8080/order_res"),
            "deviceTypeCode": request.form.get('deviceTypeCode', "pc"),
            "shopOrderNo": request.form.get('shopOrderNo', "20210326085908"),
            "orderInfo": {"goodsName": request.form.get('goodsName', "생감자튀김")}
        }

        response = requests.post(API_URL, json=data)
        response_json = response.json()
        authorization_url = response_json.get("authPageUrl")

        if authorization_url:
            return redirect(authorization_url)
        else:
            return jsonify({"error": "Authorization URL not found"})

    return render_template("order.html")  # HTML 템플릿 사용

@app.route('/order_res', methods=['POST'])
def order_response():
    """ 요청된 데이터를 받아 APPROVAL_URL로 전송하는 엔드포인트 """

    # 요청 헤더 정보 출력
    print("\n=== [ 요청 수신 ] ===")
    print("Request Headers:", request.headers)

    # mallId 가져오기 (없으면 기본값 설정)
    mall_id = session.get('mallId', 'T0001997')

    # 요청 데이터 처리
    if request.content_type == 'application/json':
        data = request.get_json(silent=True)  # JSON 데이터 처리
        print("📌 JSON 데이터 수신:", data)
    
    elif request.content_type == 'application/x-www-form-urlencoded':
        data = request.form.to_dict()  # 폼 데이터 처리
        print("📌 폼 데이터 수신:", data)
    
    else:
        data = request.data.decode('utf-8')  # JSON도 폼 데이터도 아닌 경우, 일반 텍스트로 변환
        print("📌 일반 데이터 수신:", data)

    print("====================\n")

    if not data:
        return jsonify({"error": "No data received"}), 400

    # shopTransactionId & approvalReqDate 생성
    shop_transaction_id = generate_shop_transaction_id()
    approval_req_date = generate_approval_req_date()

    # mallId, shopTransactionId, approvalReqDate 추가
    if isinstance(data, dict):
        data["mallId"] = mall_id  # JSON인 경우 mallId 추가
        data["shopTransactionId"] = shop_transaction_id  # 고유한 트랜잭션 ID 추가
        data["approvalReqDate"] = approval_req_date  # 승인 요청 날짜 추가
    else:
        data = {
            "mallId": mall_id,
            "shopTransactionId": shop_transaction_id,
            "approvalReqDate": approval_req_date,
            "rawData": data  # 문자열이면 mallId 포함
        }

    # 받은 데이터를 APPROVAL_URL로 JSON POST 요청
    try:
        approval_response = requests.post(APPROVAL_URL, json=data)
        approval_response_json = approval_response.json()  # JSON 변환
        
        print("✅ 승인 응답:", approval_response_json)  # 응답 로깅
        
        # 응답 데이터를 템플릿으로 전달
        return render_template('order_res.html', approval_response=approval_response_json, status_code=approval_response.status_code)
        content_type='text/html; charset=utf-8'  # UTF-8 인코딩을 명시적으로 지정

    except requests.RequestException as e:
        print("❌ 승인 요청 실패:", str(e))  # 오류 로깅
        return jsonify({"error": "Approval request failed", "details": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
