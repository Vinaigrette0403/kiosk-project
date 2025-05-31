from flask import Flask, render_template, request, redirect, url_for, session
import json
from flask import session
from flask import send_file
from gtts import gTTS
import os


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
    session.clear()
    return render_template('payfin.html')


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
    # 적립 1회 제한
    if session.get('earned'):
        session['message'] = "이미 적립이 완료된 주문입니다."
        return redirect(url_for('payment'))

    phone = request.form.get('phone')
    order = session.get('order', [])
    count = sum(item['count'] for item in order)

    if not phone:
        session['message'] = "전화번호를 입력하세요."
        return redirect(url_for('payment'))

    if phone not in user_points:
        user_points[phone] = {'count': 0, 'coupon': False}

    user_points[phone]['count'] += count

    if user_points[phone]['count'] >= 5:
        user_points[phone]['coupon'] = True
        user_points[phone]['count'] = 0
        session['message'] = "쿠폰이 발급되었습니다!"
    else:
        session['message'] = "적립이 완료되었습니다."

    save_points()

    session['phone'] = phone
    session['earned'] = True  # ✅ 적립 완료 표시
    return redirect(url_for('payment'))

@app.route('/use_coupon', methods=['POST'])
def use_coupon():
    phone = request.form.get('phone')

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

if __name__ == '__main__':
    app.run(debug=True)