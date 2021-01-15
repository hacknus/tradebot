from bittrex_exchange import BittrexWrapper
from mav import MAV
import matplotlib.pyplot as plt
from coin import Coin
import pandas as pd
import numpy as np


def buy_condition(mavs):
    if mavs[0].mav[-1] < mavs[1].mav[-1] < mavs[2].mav[-1] < mavs[3].mav[-1]:
        return True
    else:
        return False


def sell_condition(mavs):
    if mavs[0].mav[-1] > mavs[1].mav[-1] > mavs[2].mav[-1] > mavs[3].mav[-1]:
        return True
    else:
        return False


def test_run(profit=1.1, max_loss=0.8):
    mav5 = MAV(5)
    mav8 = MAV(8)
    mav13 = MAV(13)
    mav21 = MAV(21)

    mavs = [mav5, mav8, mav13, mav21]

    btc = Coin()

    # exchange = BittrexWrapper()

    initial_stake = 100
    wallet_usd = initial_stake
    wallet_btc = 0

    i = 100
    num_trades = 0
    df = pd.read_csv("Data/BittrexHistory.csv")
    price = np.array(df.Close)
    price = price[range(len(price) - 1, 0, -1)]
    print(f"full length: {len(price)}")
    while i < len(price):
        if i % 100 == 0:
            print(f"{i}/{len(price)}")
        # buy, sell = exchange.get_price('BTC-USD')
        sell = price[:i]
        buy = price[:i]
        p = np.array([buy, sell]).reshape(i, 2)
        btc.update(buy, sell)
        for mav in mavs:
            mav.add(p)

        if btc.last_buy == 0:
            if buy_condition(mavs):
                # if exchange.buy('BTC-USD'):
                btc.buy(buy[-1])
                wallet_btc = wallet_usd / buy[-1]
                wallet_usd = 0
                num_trades += 1
        else:
            if sell[-1] < max_loss * btc.last_buy:
                print("--------------------- LOST!")
            if sell_condition(mavs):
                # if exchange.sell('BTC-USD'):
                btc.sell()
                wallet_usd = sell[-1] * wallet_btc
                wallet_btc = 0
                num_trades += 1
        i += 1

    if wallet_usd == 0:
        wallet_usd = sell[-1] * wallet_btc
        wallet_btc = 0
    print(f"did {num_trades // 2} trades!")
    print(f"made a profit of {100 / initial_stake * wallet_usd - 100:.2f} %")
    print(f"wallet: {wallet_usd:.2f} USD")
    hodl = initial_stake / price[0] * price[i-1]
    print(f"compare wallet: {hodl:.2f} USD")
    if 100 / hodl * wallet_usd > 100:
        print(f"[OK] {100 / hodl * wallet_usd - 100:.2f} more effective than hodl")
    else:
        print(f"[FAIL] {100 - 100 / hodl * wallet_usd:.2f} less effective than hodl")


if __name__ == "__main__":
    test_run()
