from flask import Flask, request, jsonify, redirect, render_template, session
import requests
import datetime
import random
from flask_bootstrap import Bootstrap
from pyngrok import ngrok

app = Flask(__name__)
app.secret_key = "fresh_cut_fries"
Bootstrap(app)  # Flask-Bootstrap 초기화

#API_URL = "https://devpgapi.easypay.co.kr/api/ep9/trades/webpay"
API_URL = "https://testpgapi.easypay.co.kr/api/ep9/trades/webpay"
#APPROVAL_URL = "https://devpgapi.easypay.co.kr/api/ep9/trades/approval"
APPROVAL_URL = "https://testpgapi.easypay.co.kr/api/ep9/trades/approval"

# 메뉴 데이터
MENU_DATA = {
    "burgers": [
        {"id": "bigmac", "name": "빅맥", "price": 6500, "description": "두 개의 순 쇠고기 패티와 특별한 소스", "image": "🍔"},
        {"id": "whopper", "name": "와퍼", "price": 7200, "description": "불에 구운 쇠고기 패티와 신선한 야채", "image": "🍔"},
        {"id": "cheeseburger", "name": "치즈버거", "price": 4800, "description": "클래식한 치즈버거의 정석", "image": "🍔"},
        {"id": "bacon_burger", "name": "베이컨 버거", "price": 6800, "description": "바삭한 베이컨과 육즙 가득한 패티", "image": "🥓"},
        {"id": "mushroom_burger", "name": "머쉬룸 스위스 버거", "price": 7500, "description": "버섯과 스위스 치즈의 조화", "image": "🍄"},
        {"id": "chicken_burger", "name": "치킨 버거", "price": 6200, "description": "바삭한 프라이드 치킨 패티", "image": "🐔"}
    ],
    "sides": [
        {"id": "fries", "name": "감자튀김", "price": 2800, "description": "바삭바삭한 황금 감자튀김", "image": "🍟"},
        {"id": "cheese_fries", "name": "치즈 프라이", "price": 3500, "description": "치즈가 듬뿍 올라간 감자튀김", "image": "🧀"},
        {"id": "onion_rings", "name": "어니언링", "price": 3200, "description": "바삭한 양파링", "image": "🧅"},
        {"id": "nuggets", "name": "치킨 너겟 (6조각)", "price": 4200, "description": "바삭한 치킨 너겟", "image": "🍗"},
        {"id": "mozzarella_sticks", "name": "모짜렐라 스틱", "price": 4800, "description": "쫄깃한 모짜렐라 치즈 스틱", "image": "🧀"}
    ],
    "drinks": [
        {"id": "coke", "name": "코카콜라", "price": 2200, "description": "시원한 코카콜라", "image": "🥤"},
        {"id": "sprite", "name": "스프라이트", "price": 2200, "description": "상쾌한 스프라이트", "image": "🥤"},
        {"id": "orange", "name": "오렌지 주스", "price": 2800, "description": "100% 순수 오렌지 주스", "image": "🍊"},
        {"id": "milkshake_vanilla", "name": "바닐라 쉐이크", "price": 3800, "description": "부드러운 바닐라 밀크쉐이크", "image": "🥛"},
        {"id": "milkshake_strawberry", "name": "딸기 쉐이크", "price": 3800, "description": "달콤한 딸기 밀크쉐이크", "image": "🍓"},
        {"id": "coffee", "name": "아이스 아메리카노", "price": 2500, "description": "진한 아이스 아메리카노", "image": "☕"}
    ],
    "desserts": [
        {"id": "apple_pie", "name": "애플파이", "price": 2800, "description": "따뜻한 사과파이", "image": "🥧"},
        {"id": "ice_cream", "name": "바닐라 아이스크림", "price": 2200, "description": "부드러운 바닐라 아이스크림", "image": "🍦"},
        {"id": "cookies", "name": "초콜릿 쿠키", "price": 1800, "description": "바삭한 초콜릿 쿠키", "image": "🍪"},
        {"id": "brownie", "name": "초콜릿 브라우니", "price": 3200, "description": "진한 초콜릿 브라우니", "image": "🧁"}
    ]
}

def generate_shop_transaction_id():
    """ 고유한 shopTransactionId 생성 """
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    random_number = str(random.randint(0, 999999)).zfill(6)
    return f"fresh{now}{random_number}"

def generate_approval_req_date():
    """ 승인 요청 날짜 (YYYYMMDD) 생성 """
    return datetime.datetime.now().strftime("%Y%m%d")

def get_item_by_id(item_id):
    """아이템 ID로 메뉴 아이템 찾기"""
    for category in MENU_DATA.values():
        for item in category:
            if item['id'] == item_id:
                return item
    return None

@app.route('/')
def index():
    return render_template("burger_order.html", menu_data=MENU_DATA)

@app.route('/order', methods=['POST'])
def process_order():
    cart_data = request.get_json()
    
    if not cart_data or not cart_data.get('items'):
        return jsonify({"error": "장바구니가 비어있습니다"}), 400
    
    # 장바구니 아이템들과 총 금액 계산
    order_items = []
    total_amount = 0
    
    for item in cart_data['items']:
        menu_item = get_item_by_id(item['id'])
        if menu_item:
            item_total = menu_item['price'] * item['quantity']
            total_amount += item_total
            order_items.append({
                'name': menu_item['name'],
                'price': menu_item['price'],
                'quantity': item['quantity'],
                'total': item_total
            })
    
    # 세션에 주문 정보 저장
    session['order_items'] = order_items
    session['total_amount'] = total_amount
    session['payment_method'] = cart_data.get('paymentMethod', '11')
    session['mallId'] = 'T0001997'
    
    # 상품명 생성 (첫 번째 아이템명 + 외 N개)
    if len(order_items) == 1:
        goods_name = order_items[0]['name']
    else:
        goods_name = f"{order_items[0]['name']} 외 {len(order_items)-1}개"

    # ngrok public URL 가져오기
    public_url = app.config.get('PUBLIC_URL', '')
    print(public_url)
    return_url = f"{public_url}/order_result" if public_url else "http://192.168.15.89:5000/order_result"
    
    # 이지페이 결제 요청
    data = {
        "mallId": "T0001997",
        "payMethodTypeCode": cart_data.get('paymentMethod', '11'),
        "currency": "00",
        "amount": total_amount,
        "clientTypeCode": "00",
        "returnUrl": return_url,
        "deviceTypeCode": "pc",
        "shopOrderNo": generate_shop_transaction_id(),
        "orderInfo": {"goodsName": goods_name}
    }
    
    try:
        response = requests.post(API_URL, json=data)
        response_json = response.json()
        authorization_url = response_json.get("authPageUrl")
        
        if authorization_url:
            return jsonify({"authPageUrl": authorization_url})
        else:
            return jsonify({"error": "결제 페이지를 불러올 수 없습니다"}), 500
            
    except Exception as e:
        return jsonify({"error": "결제 요청 중 오류가 발생했습니다"}), 500

@app.route('/order_result', methods=['POST'])
def order_response():
    """ 결제 완료 후 승인 처리 """
    print("\n=== [ 결제 승인 요청 수신 ] ===")
    print("Request Headers:", request.headers)
    
    mall_id = session.get('mallId', 'T0001997')
    
    # 요청 데이터 처리
    if request.content_type == 'application/json':
        data = request.get_json(silent=True)
        print("📌 JSON 데이터 수신:", data)
    elif request.content_type == 'application/x-www-form-urlencoded':
        data = request.form.to_dict()
        print("📌 폼 데이터 수신:", data)
    else:
        data = request.data.decode('utf-8')
        print("📌 일반 데이터 수신:", data)
    
    print("====================\n")
    
    if not data:
        return jsonify({"error": "승인 데이터를 받지 못했습니다"}), 400
    
    # shopTransactionId & approvalReqDate 생성
    shop_transaction_id = generate_shop_transaction_id()
    approval_req_date = generate_approval_req_date()
    
    # 승인 요청 데이터 구성
    if isinstance(data, dict):
        data["mallId"] = mall_id
        data["shopTransactionId"] = shop_transaction_id
        data["approvalReqDate"] = approval_req_date
    else:
        data = {
            "mallId": mall_id,
            "shopTransactionId": shop_transaction_id,
            "approvalReqDate": approval_req_date,
            "rawData": data
        }
    
    # 승인 요청
    try:
        approval_response = requests.post(APPROVAL_URL, json=data)
        approval_response_json = approval_response.json()
        
        print("✅ 승인 응답:", approval_response_json)
        
        # 주문 정보 가져오기
        order_items = session.get('order_items', [])
        total_amount = session.get('total_amount', 0)
        
        return render_template('order_result.html', 
                             approval_response=approval_response_json,
                             status_code=approval_response.status_code,
                             order_items=order_items,
                             total_amount=total_amount)
        
    except requests.RequestException as e:
        print("❌ 승인 요청 실패:", str(e))
        return jsonify({"error": "승인 요청에 실패했습니다", "details": str(e)}), 500

if __name__ == '__main__':
    port = 5000
    public_url = ngrok.connect(port)
    print("Public URL:", public_url)
    app.config['PUBLIC_URL'] = public_url

    app.run(host='0.0.0.0', port=port)