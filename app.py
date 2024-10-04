from flask import Flask, render_template, jsonify, session, redirect, url_for, request
from account import account_bp
import os, glob, random, json
from db import get_db

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.register_blueprint(account_bp)

def get_user_money(steam_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT money FROM users WHERE steam_id = ?', (steam_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

@app.context_processor
def inject_user_money():
    if 'steam_id' in session:
        return {'money': get_user_money(session['steam_id'])}
    return {'money': 0}

@app.route('/')
def index():
    if 'steam_id' in session:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT current_planet_id FROM users WHERE steam_id = ?', (session['steam_id'],))
        result = cursor.fetchone()
        current_planet_id = result['current_planet_id'] if result else 225
    else:
        current_planet_id = 225

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM planets WHERE id = ?', (current_planet_id,))
    current_planet = cursor.fetchone()
    current_planet = dict(current_planet)
    current_planet['info'] = json.loads(current_planet['info'])

    return render_template('index.html', current_planet=current_planet)


@app.route('/change_planet', methods=['POST'])
def change_planet():
    if 'steam_id' not in session:
        return redirect(url_for('account.login'))

    planet_id = request.json['planet_id']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET current_planet_id = ? WHERE steam_id = ?', (planet_id, session['steam_id']))
    conn.commit()

    return jsonify({'status': 'success', 'planet_id': planet_id, 'message': 'Planet changed successfully'})

@app.route('/shop')
def shop():
    if 'steam_id' not in session:
        return redirect(url_for('account.login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM inventories JOIN planets ON inventories.planet_id = planets.id WHERE status = ? AND steam_id != ? ORDER BY updated_at DESC', ('selling', session['steam_id']))
    selling_items = cursor.fetchall()
    
    return render_template('shop.html', selling_items=selling_items)

@app.route('/buy_item', methods=['POST'])
def buy_item():
    if 'steam_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})

    item_id = request.json['item_id']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM inventories WHERE id = ? AND status = ?', (item_id, 'selling'))
    item = cursor.fetchone()
    seller_id = item['steam_id']

    if not item:
        return jsonify({'status': 'error', 'message': 'Item not found'})

    if get_user_money(session['steam_id']) < item['price']:
        return jsonify({'status': 'error', 'message': 'Not enough money'})

    cursor.execute('UPDATE inventories SET steam_id = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (session['steam_id'], 'inventory', item_id))
    cursor.execute('UPDATE users SET money = money - ? WHERE steam_id = ?', (item['price'], session['steam_id']))
    cursor.execute('UPDATE users SET money = money + ? WHERE steam_id = ?', (item['price'], seller_id))
    conn.commit()

    return jsonify({'status': 'success', 'message': 'Planet bought successfully', 'money': get_user_money(session['steam_id'])})

@app.route('/inventory')
def inventory():
    if 'steam_id' not in session:
        return redirect(url_for('account.login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM inventories JOIN planets ON inventories.planet_id = planets.id WHERE steam_id = ? ORDER BY created_at DESC', (session['steam_id'],))
    inventory = cursor.fetchall()
    return render_template('inventory.html', inventory=inventory)

@app.route('/sell_item', methods=['POST'])
def sell_item():
    if 'steam_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})

    item_id = request.json['item_id']
    price = int(request.json['price'])

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM inventories WHERE id = ? AND steam_id = ?', (item_id, session['steam_id']))
    item = cursor.fetchone()

    if not item:
        return jsonify({'status': 'error', 'message': 'Item not found'})

    cursor.execute('UPDATE inventories SET price = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (price, 'selling', item_id))
    conn.commit()

    return jsonify({'status': 'success', 'message': 'Item registered successfully', 'money': get_user_money(session['steam_id'])})

@app.route('/cancel_sell_item', methods=['POST'])
def cancel_sell_item():
    if 'steam_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})

    item_id = request.json['item_id']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE inventories SET price = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND steam_id = ?', (0, 'inventory', item_id, session['steam_id']))
    conn.commit()

    return jsonify({'status': 'success', 'message': 'Planet registration canceled successfully', 'money': get_user_money(session['steam_id'])})

@app.route('/delete_item', methods=['POST'])
def delete_item():
    if 'steam_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})

    item_id = request.json['item_id']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM inventories WHERE id = ? AND steam_id = ?', (item_id, session['steam_id']))
    cursor.execute('UPDATE users SET money = money + ? WHERE steam_id = ?', (10, session['steam_id']))
    conn.commit()

    return jsonify({'status': 'success', 'message': 'Planet deleted successfully', 'money': get_user_money(session['steam_id'])})

@app.route('/drop_planet')
def drop_planet():
    if 'steam_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM planets')
    planets = cursor.fetchall()

    random_planet = random.choices(planets, weights=[planet['probability'] for planet in planets])[0]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO inventories (steam_id, planet_id) VALUES (?, ?)
    ''', (session['steam_id'], random_planet['id']))
    conn.commit()
    last_id = cursor.lastrowid

    random_planet = dict(random_planet)
    random_planet['last_id'] = last_id

    return jsonify({'status': 'success', 'planet': random_planet})

if __name__ == '__main__':
    app.run(debug=True, port=5051, host='0.0.0.0')
