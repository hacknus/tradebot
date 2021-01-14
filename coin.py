import pandas as pd


class Coin:

    def __init__(self):
        d = {
            "sell": [],
            "buy": []
        }
        self.df = pd.DataFrame.from_dict(data=d)
        self.last_buy = 0

    def update(self, buy, sell):
        self.df = self.df.append({'buy': buy, 'sell': sell}, ignore_index=True)

    def buy(self, price):
        self.last_buy = price

    def sell(self):
        self.last_buy = 0


if __name__ == "__main__":
    BTC = Coin()
    BTC.update(10, 11)
    BTC.update(11, 12)
    print(BTC.df.head())
