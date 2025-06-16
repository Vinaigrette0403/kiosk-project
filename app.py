from flask import Flask, render_template, request, redirect, url_for, session
import json
from flask import session
from flask import send_file
from gtts import gTTS
import os
import re

ORDER_FILE = 'order_number.json'

# 서버 시작 시 주문번호 불러오기
if os.path.exists(ORDER_FILE):
    with open(ORDER_FILE, 'r') as f:
        current_order_number = json.load(f).get("order_number", 1)
else:
    current_order_number = 1

def save_order_number():
    with open(ORDER_FILE, 'w') as f:
        json.dump({"order_number": current_order_number}, f)

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATA_FILE = 'user_points.json'

menu_items = {
    '아메리카노': 4000,
    '카페라떼': 4500,
    '초코라떼': 5000,
    '녹차라떼': 5000,
    '딸기라떼': 5500,
    '바닐라라떼': 5000,
    '아이스티' : 3000
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu')
def menu():
    return render_template('menu.html', menu_items=menu_items)

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if request.method == 'POST':
        data = request.get_json()
        session['order'] = data.get('order', [])
        return '', 204  

    else:  
        order = session.get('order', [])
        total = sum(item['count'] * item['price'] for item in order)
        coupon_used = session.get('coupon', False)
        total_with_coupon = total - 2000 if coupon_used else total
        return render_template('payment.html', order=order, total=total, total_with_coupon=total_with_coupon)

@app.route('/payfin')
def payfin():
    global current_order_number

    formatted_order_number = f"{current_order_number:04d}"  # 예: 0001

    # 다음 번호로 증가 (0010 넘으면 0001로)
    current_order_number = current_order_number + 1 if current_order_number < 10 else 1
    save_order_number()

    session.clear()
    return render_template('payfin.html', order_number=formatted_order_number)



@app.route('/voice_order', methods=['POST'])
def voice_order():
    data = request.get_json()
    item_name = data.get('item', '').strip()

    if item_name in menu_items:
        price = menu_items[item_name]

        
        order = session.get('order', [])
        for item in order:
            if item['name'] == item_name:
                item['count'] += 1
                break
        else:
            order.append({
                'name': item_name,
                'count': 1,
                'price': price
            })
        session['order'] = order

        
        return jsonify({"name": item_name, "price": price})

    else:
        return '메뉴없음', 400

@app.route('/speak/<text>')
def speak(text):
    tts = gTTS(text=text, lang='ko')
    filename = f"static/tts/selected.mp3"
    tts.save(filename)
    return send_file(filename, mimetype="audio/mpeg")

# 프로그램 시작 시 JSON 파일에서 로드
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        user_points = json.load(f)
else:
    user_points = {}  # 예: {'01012345678': {'count': 3, 'coupon': False}}

# 수정 시 저장 함수
def save_points():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_points, f, ensure_ascii=False)

@app.route('/earn_point', methods=['POST'])
def earn_point():
    if session.get('earned'):
        session['message'] = "이미 적립이 완료된 주문입니다."
        return redirect(url_for('payment'))

    phone = request.form.get('phone')
    order = session.get('order', [])
    count = sum(item['count'] for item in order)

    if not re.match(r'^010\d{7,8}$', phone):
        session['message'] = "유효한 전화번호를 입력하세요. (예: 01012345678)"
        return redirect(url_for('payment'))
    if not phone:
        session['message'] = "전화번호를 입력하세요."
        return redirect(url_for('payment'))

    if phone not in user_points:
        user_points[phone] = {'count': 0, 'coupon': False}

    # ✅ 누적 계산
    total_count = user_points[phone]['count'] + count
    coupon_count = total_count // 5
    remaining = total_count % 5

    if coupon_count >= 1:
        user_points[phone]['coupon'] = True
        user_points[phone]['count'] = remaining
        session['message'] = f"쿠폰이 발급되었습니다! 현재 {remaining}/5잔 적립 중입니다."
    else:
        user_points[phone]['count'] = total_count
        session['message'] = f"적립이 완료되었습니다. 현재 {total_count}/5잔 적립 중입니다."

    save_points()
    session['phone'] = phone
    session['earned'] = True
    return redirect(url_for('payment'))

@app.route('/use_coupon', methods=['POST'])
def use_coupon():
    phone = request.form.get('phone')

    
    if not re.match(r'^010\d{7,8}$', phone):
        session['message'] = "유효한 전화번호를 입력하세요. (예: 01012345678)"
        return redirect(url_for('payment'))
    if phone in user_points and user_points[phone].get('coupon'):
        session['coupon'] = True
        user_points[phone]['coupon'] = False
        session['message'] = "쿠폰이 적용되었습니다! 2,000원 할인"
        save_points()
    else:
        session['coupon'] = False
        session['message'] = "사용 가능한 쿠폰이 없습니다."

    session['phone'] = phone
    return redirect(url_for('payment'))

@app.route('/check_stamp', methods=['POST'])
def check_stamp():
    phone = request.form.get('phone')
    
    if not re.match(r'^010\d{7,8}$', phone):
        session['message'] = "유효한 전화번호를 입력하세요. (예: 01012345678)"
        return redirect(url_for('payment'))
    if not phone:
        session['message'] = "전화번호를 입력해주세요."
        return redirect(url_for('payment'))
    
    user = user_points.get(phone)
    
    if user:
        stamp = user.get('count', 0)
        coupon = 1 if user.get('coupon', False) else 0
        session['message'] = f"현재 스탬프 {stamp}/5개, 쿠폰 {coupon}장 보유 중입니다."
    else:
        session['message'] = "등록된 정보가 없습니다."

    return redirect(url_for('payment'))

if __name__ == '__main__':
    app.run(debug=True)