import os
import sys
import json
from datetime import datetime

import requests
from flask import Flask, request, send_file

import moltin
from moltin_token import get_token

app = Flask(__name__)
_database = None
moltin_token = None
moltin_token_time = 0


@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):  # someone sent us a message
                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text
                    send_menu(sender_id, message_text)
    return "ok", 200


@app.route('/get_image', methods=['GET'])
def get_logo():
    if request.args.get('type') == '1':
       filename = 'img/pizza_logo.png'
    else:
       return "Bad request", 400

    return send_file(filename, mimetype='image/gif')


def send_menu(recipient_id, message_text):
    elements = get_menu_keyboard_content()
    params = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
    headers = {"Content-Type": "application/json"}
    request_content = json.dumps({
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "generic",
                        "image_aspect_ratio": "square",
                        "elements": elements
                    }
                }
            }
        })
    url = 'https://graph.facebook.com/v2.6/me/messages'
    response = requests.post(url, params=params, headers=headers, data=request_content)
    response.raise_for_status()
    

def get_menu_keyboard_content():
    global moltin_token
    global moltin_token_time
    moltin_token, moltin_token_time = get_token(moltin_token, moltin_token_time)

    elements = [{
                    "title": "Меню",
                    "image_url": "https://8f2c1832d211.ngrok.io/get_image?type=1",
                    "subtitle": "Здесь вы можете выбрать один из вариантов",
                    "buttons": [
                        {
                            "type": "postback",
                            "title": "Корзина",
                            "payload": "cart",
                        },
                        {
                            "type": "postback",
                            "title": "Акции",
                            "payload": "event",
                        },
                        {
                            "type": "postback",
                            "title": "Сделать заказ",
                            "payload": "order",
                        },
                    ]
                }]
    products = moltin.get_products_list(moltin_token)[0:4]
    for product in products:
        title = f'{product["name"]} ({product["price"]}р.)'
        description = product['description']
        image_url = moltin.get_image_url(moltin_token, product['image_id'])
        elements.append({
                    "title": title,
                    "image_url": image_url,
                    "subtitle": description,
                    "buttons": [
                        {
                            "type": "postback",
                            "title": "Добавить в корзину",
                            "payload": "add_to_cart",
                        },
                    ]
                })

    return elements


if __name__ == '__main__':
    app.run(debug=True)
