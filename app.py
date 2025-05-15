from flask import Flask, render_template, request, redirect, url_for, session
import json
from flask import session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 음료와 가격 정보
menu_items = {
    '아메리카노': 4000,
    '카페라떼': 4500,
    '초코라떼': 5000,
    '녹차라떼': 5000,
    '딸기라떼': 5500,
    '바닐라라떼': 5000
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
        return redirect(url_for('payment'))  # POST → redirect to GET
    else:
        order = session.get('order', [])
        total = sum(item['count'] * item['price'] for item in order)
        return render_template('payment.html', order=order, total=total)

@app.route('/finish_payment')
def finish_payment():
    session.pop('cart', None)
    session.pop('total_price', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
