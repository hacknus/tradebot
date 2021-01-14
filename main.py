from bittrex_exchange import BittrexWrapper
from mav import MAV
from coin import Coin


def buy_condition(mavs):
    if mavs[0].mav < mavs[1].mav < mavs[2].mav < mavs[3].mav:
        return True
    else:
        return False


def sell_condition(mavs):
    if mavs[0].mav > mavs[1].mav > mavs[2].mav > mavs[3].mav:
        return True
    else:
        return False


def main(profit=1.1, max_loss=0.8):
    mav5 = MAV(5)
    mav8 = MAV(8)
    mav13 = MAV(13)
    mav21 = MAV(21)

    mavs = [mav5, mav8, mav13, mav21]

    btc = Coin()

    exchange = BittrexWrapper()

    while True:
        buy, sell = exchange.get_price('BTC-USD')
        Coin.update(buy, sell)

        if btc.last_buy != 0:
            if buy_condition(mavs):
                if exchange.buy('BTC-USD'):
                    btc.buy(buy)
        else:
            if sell_condition(mavs) or sell > profit * btc.last_buy or sell < max_loss * btc.last_buy:
                if exchange.sell('BTC-USD'):
                    btc.sell()


if __name__ == "__main__":
    main()
