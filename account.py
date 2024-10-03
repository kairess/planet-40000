from flask import Flask, redirect, url_for, session, render_template, Blueprint
from flask_openid import OpenID
import requests, os
from datetime import datetime, timezone
from db import get_db

account_bp = Blueprint('account', __name__)
oid = OpenID()

STEAM_API_KEY = os.getenv('STEAM_API_KEY')

@account_bp.route('/login')
@oid.loginhandler
def login():
    return oid.try_login('https://steamcommunity.com/openid')

@oid.after_login
def create_or_login(resp):
    steam_id = resp.identity_url.split('/')[-1]
    session['steam_id'] = steam_id

    user_info_url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={STEAM_API_KEY}&steamids={steam_id}'
    user_info = requests.get(user_info_url).json()

    session['steam_name'] = user_info['response']['players'][0]['personaname'] if 'personaname' in user_info['response']['players'][0] else user_info['response']['players'][0]['realname']
    session['steam_avatar'] = user_info['response']['players'][0]['avatarfull']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE steam_id = ?', (steam_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('INSERT INTO users (steam_id) VALUES (?)', (steam_id,))
        conn.commit()
    else:
        current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('UPDATE users SET last_login = ?, login_count = ? WHERE steam_id = ?', (current_time, user['login_count'] + 1, steam_id))
        conn.commit()

    return redirect(url_for('index'))

@account_bp.route('/logout')
def logout():
    session.pop('steam_id', None)
    return redirect(url_for('index'))