import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode

API_KEY = 'mx0vgllZiIlTWjzJza'
SECRET_KEY = '3d8e56ced55c480aa9b25aa3004a551f'

session = requests.Session()
session.headers.update({'X-MEXC-APIKEY': API_KEY})

def sign(params: dict) -> str:
    query_string = urlencode(sorted(params.items()), doseq=True).replace('+', '%20')
    return hmac.new(
        SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def place_limit_order(symbol: str, side: str, quantity: str, price: str):
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

# Пример вызова:
print('x')
start = time.time()
status, text = place_limit_order('RENTAUSDT', 'BUY', '200', '0.01')
print(status, text)
print(time.time() - start)