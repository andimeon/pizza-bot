import os
import requests
import logging
import json

from flask import Flask, request, send_file
import redis
from environs import Env

import fb_menu_keyboard, fb_help_keyboard
from moltin_token import get_token

app = Flask(__name__)
_database = None
moltin_token = None
moltin_token_time = 0

env = Env()
env.read_env()


@app.route('/', methods=['GET'])
def verify():
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == env('VERIFY_TOKEN'):
            return 'Verification token mismatch', 403
        return request.args['hub.challenge'], 200
    return 'Hello world', 200


def handle_start(sender_id, message):
    fb_menu_keyboard.send_menu(sender_id, moltin_token, message)
    return 'START'


def handle_help(sender_id, message):
    fb_help_keyboard.send_help_message(sender_id, message)
    return 'START'


def handle_users_reply(sender_id, message_text):
    global moltin_token
    global moltin_token_time
    moltin_token, moltin_token_time = get_token(moltin_token, moltin_token_time)
    db = get_database_connection()

    states_functions = {
        'START': handle_start,
        'HELP': handle_help,
    }

    user = f'fb_{sender_id}'
    recorded_state = db.get(user)
    if not recorded_state or recorded_state.decode('utf-8') not in states_functions.keys():
        user_state = 'HELP'
    else:
        user_state = recorded_state.decode('utf-8')
    if message_text == '/start' or message_text == 'menu':
        user_state = 'START'
    elif 'start' in message_text:
        user_state = 'START'
    else:
        user_state = 'HELP'
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(sender_id, message_text)
        db.set(user, next_state)
    except Exception as err:
        logging.exception(err)


@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if data['object'] == 'page':
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                if messaging_event.get('message'):
                    sender_id = messaging_event['sender']['id']
                    # recipient_id = messaging_event["recipient"]["id"]
                    message = messaging_event['message']['text']
                    handle_users_reply(sender_id, message)
                elif messaging_event.get('postback'):
                    sender_id = messaging_event['sender']['id']
                    payload = messaging_event['postback']['payload']
                    handle_users_reply(sender_id, payload)
    return "ok", 200


@app.route('/get_image', methods=['GET'])
def get_image():
    if request.args.get('type') == '1':
        filename = 'img/pizza_logo.png'
    elif request.args.get('type') == '2':
        filename = 'img/pizza_category.jpg'
    else:
        return "Bad request", 400

    return send_file(filename, mimetype='image/gif')


def get_database_connection():
    global _database
    if _database is None:
        database_password = env("DATABASE_PASSWORD")
        database_host = env("DATABASE_HOST")
        database_port = env("DATABASE_PORT")

        _database = redis.Redis(host=database_host,
                                port=database_port,
                                password=database_password)
    return _database


if __name__ == '__main__':
    app.run(debug=True)