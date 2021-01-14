from bittrex_exchange import BittrexWrapper as BTRX


class BittrexWrapper(BTRX):
    def __init__self(self):
        # wrapper for Bittrex exchange
        self.drop = False
        self.climb = False
        self.current_price = 0
        self.last_price = 0


class CoinbaseWrapper:
    def __init__(self):
        # dummy wrapper
        self.drop = False
        self.climb = False
        self.current_price = 0
        self.last_price = 0

    def get_price(self, pair):
        pass

    def sell(self, pair):
        pass


class BitfinexWrapper:
    def __init__(self):
        # dummy wrapper
        self.drop = False
        self.climb = False
        self.current_price = 0
        self.last_price = 0

    def get_price(self, pair):
        pass

    def sell(self, pair):
        pass


class BinanceWrapper:
    def __init__(self):
        # dummy wrapper
        self.drop = False
        self.climb = False
        self.current_price = 0
        self.last_price = 0

    def get_price(self, pair):
        pass

    def sell(self, pair):
        pass


def compare_exchanges(exchanges):
    # dummy function
    return exchanges[0], exchanges[1]


def main():
    fee = 0.0001  # insert maximum fee of all exchanges
    binance = Binance_wrapper()
    bittrex = Bittrex_wrapper()
    coinbase = Coinbase_wrapper()
    bitfinex = Bitfinex_wrapper()
    bought = False

    while True:
        if not bought:
            first, last = compare_exchanges([binance, bittrex, coinbase, bitfinex])
        if first.climb:
            last.buy()
            last.last_price = 0  # get last bought price
            bought = True
        if first.drop and bought and last.last_price + fee < last.current_price:
            last.sell()
            bought = False


if __name__ == "__main__":
    main()
