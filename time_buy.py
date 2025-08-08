import json
import time

from main import cancel_order, place_limit_order, symbol, ask, bid, quantity


time_sleep = 0.15
time_active = 0.05

def main():
    while True:
        status, text = place_limit_order(symbol=f"{symbol}USDT", side='BUY', price=str(round(bid + 0.000001, 6)))
        time.sleep(time_active)
        cancel_order(symbol, json.loads(text)['orderId'])
        time.sleep(time_sleep)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Program interrupted by user.")