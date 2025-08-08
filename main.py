from datetime import datetime
import websocket
import threading
import time
import PushDataV3ApiWrapper_pb2
import logging
import json
import hmac
import hashlib
from urllib.parse import urlencode
import requests

# Конфигурация
API_KEY = "mx0vgllZiIlTWjzJza"
API_SECRET = "3d8e56ced55c480aa9b25aa3004a551f"

symbol = input("Enter the symbol: ")
ask = float(input("Enter the ask price: "))
bid = float(input("Enter the bid price: "))
quantity = float(input("Enter the quantity: "))
type_search = input("Enter the type search (T/A) Trade/Analysis: ")
prices = {'ask': ask, 'bid': bid}

last_trade = time.time()
time_buy = time.time()
time_sell = time.time()
time_active = 0.1

BASE_URL = 'wss://wbs-api.mexc.com/ws'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Сессия requests с заголовком
session = requests.Session()
session.headers.update({'X-MEXC-APIKEY': API_KEY})

def sign(params: dict) -> str:
    query_string = urlencode(sorted(params.items()), doseq=True).replace('+', '%20')
    return hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def place_limit_order(symbol: str, side: str, price: str):
    timestamp = int(time.time() * 1000)
    params = {
        'symbol': symbol,
        'side': side,
        'type': 'LIMIT',
        'quantity': quantity,
        'price': price,
        'timeInForce': 'GTC',
        'recvWindow': 5000,
        'timestamp': timestamp
    }
    signature = sign(params)
    params['signature'] = signature
    query_string = urlencode(sorted(params.items()), doseq=True).replace('+', '%20')
    url = f'https://api.mexc.com/api/v3/order?{query_string}'

    response = session.post(url)
    return response.status_code, response.text

def logic(price: float, quantity_bot: float):
    global last_trade, time_buy, time_sell
    if not all(isinstance(x, (int, float)) for x in [price, quantity_bot]):
        logger.warning("Invalid price or quantity types")
        return

    target_price = round(prices['ask'] - 0.0000001, 6)
    if price != target_price:
        if prices['bid'] < price < prices['ask']:
            if quantity_bot > 0:
                time_buy = time.time()
                if quantity_bot != quantity:
                    logger.info(f"Attempting to place order: price={target_price}")

                    print(prices, quantity_bot)
                    if type_search == 'T':
                        status, text = place_limit_order(
                            symbol=f"{symbol}USDT",
                            side='BUY',
                            price=str(target_price)
                        )
                        if status == 200 or status == 201:
                            logger.info(f"Order placed successfully: {text}")
                        else:
                            logger.error(f"Failed to place order: Status {status}, Response: {text}")
                        time.sleep(0.1)
                        cancel_order(symbol, json.loads(text)['orderId'])
            else:
                time_sell = time.time()
                # print("Delta trade:", time_sell - time_buy)
                # last_trade = time_buy


def cancel_order(symbol: str, order_id: str):
    timestamp = int(time.time() * 1000)
    params = {
        'symbol': symbol+'USDT',
        'orderId': order_id,
        'recvWindow': 5000,
        'timestamp': timestamp
    }
    signature = sign(params)
    params['signature'] = signature
    query_string = urlencode(sorted(params.items()), doseq=True).replace('+', '%20')
    url = f'https://api.mexc.com/api/v3/order?{query_string}'
    response = session.delete(url)
    return response.status_code, response.text

def on_message(ws, message):
    try:
        if isinstance(message, str):
            try:
                json_data = json.loads(message)
                logger.info(f"Received JSON: {json_data}")
                return
            except json.JSONDecodeError:
                message = message.encode('utf-8')
        result = PushDataV3ApiWrapper_pb2.PushDataV3ApiWrapper()
        result.ParseFromString(message)
        data = result.publicAggreDepths
        if data.bids:
            price = float(data.bids[0].price)
            quantity = float(data.bids[0].quantity)
            logic(price, quantity)
        if data.asks:
            price = float(data.asks[0].price)
            quantity = float(data.asks[0].quantity)
            logic(price, quantity)

    except Exception as e:
        logger.error(f"Error parsing message: {str(e)}")
        if isinstance(message, bytes):
            logger.info(f"Binary message first 100 bytes: {message[:100].hex()}")
        elif isinstance(message, str):
            logger.info(f"String message first 100 chars: {message[:100]}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")

def on_error(ws, error):
    logger.error(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    logger.info(f"WebSocket connection closed. Status code: {close_status_code}, Message: {close_msg}")

def on_open(ws):
    logger.info("WebSocket connection opened")
    try:
        subscribe_message = {
            "method": "SUBSCRIPTION",
            "params": [
                f"spot@public.aggre.depth.v3.api.pb@10ms@{symbol}USDT"
            ]
        }
        ws.send(json.dumps(subscribe_message))
        logger.info(f"Sent subscription message: {subscribe_message}")
    except Exception as e:
        logger.error(f"Error in on_open: {str(e)}")

    def send_ping():
        while True:
            time.sleep(30)
            try:
                ws.send(json.dumps({"method": "ping"}))
            except Exception as e:
                print(f"Error sending ping: {e}")
                break

    threading.Thread(target=send_ping, daemon=True).start()




def main():
    while True:
        try:
            websocket.enableTrace(False)
            ws = websocket.WebSocketApp(BASE_URL,
                                        on_message=on_message,
                                        on_error=on_error,
                                        on_close=on_close)
            ws.on_open = on_open
            ws.run_forever(ping_interval=30, ping_timeout=10, sslopt={"cert_reqs": 0})
        except Exception as e:
            logger.error(f"Main loop error: {str(e)}")
        logger.info("Reconnecting in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program interrupted by user.")
