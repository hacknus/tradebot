from bittrex import Bittrex
import numpy as np
import time
import requests
import logging
import traceback
import os
import h5py


class Bittrex_wrapper:
    '''adapted API functions'''

    def __init__(self, logname="bittrex.log"):
        logging.basicConfig(filename=logname, level=logging.DEBUG)
        self.__API_KEY = ""
        self.__API_SECRET = ""
        self.prices = {}
        self.MAX_MEM = 7 * 60 * 60 * 24
        self.wallet = {}
        self.ignore = ["BTC-PKB", "BTC-ADA", "BTC-RISE", "BTC-STRAT", "BTC-XVG", "BTC-ENG", "BTC-FAIR", "BTC-VTC",
                       "BTC-RISE", "BTC-VIA"]
        '''
        print "\n currently not monitoring/trading these pairs:"
        for i in self.ignore:
            print i
        print "for changes: edit self.ignore list in Exchange class \n"
        '''
        logging.info(f"running a new session, time: {time.ctime()}")
        logging.info(f"not monitoring/trading following pairs: {str(self.ignore)}")
        '''read API keys'''
        try:
            file = open('keys/bittrex_key.txt', 'r')
            data = file.readlines()
            self.__API_KEY = data[0].replace('\n', '')
            self.__API_SECRET = data[1].replace('\n', '')
            file.close()
        except:
            logging.error('ERROR: no "bittrex_key.txt" found, exiting...', '')
            raise Exception('ERROR: no "bittrex_key.txt" found')

    def initial_setup(self, sell_all=False):
        my_bittrex = Bittrex(self.__API_KEY, self.__API_SECRET)
        self.wallet = my_bittrex.get_balances()['result']
        print("got wallets")
        for w in self.wallet:
            pair = 'BTC-' + str(w['Currency'])
            print(pair)
            if pair in self.prices and pair not in self.ignore:
                amount = w['Available']
                if amount > 0.0001 and sell_all:
                    print("found balance in {} -- selling to BTC!".format(pair))
                    if not self.sell(pair):
                        print("selling {} failed.. continue anyway... check log file for more info".format(pair))
            else:
                pass
        print("ok --")
        print("checking BTC wallet")
        btc_amount = my_bittrex.get_balance('BTC')['result']['Available']
        print("ok... {} BTC available to trade".format(btc_amount))
        logging.info(
            f"starting trading with {btc_amount} BTC available, monitoring {len(self.prices) - 2} "
            "currency pairs on BITTREX")
        print("starting logging/trading")
        self.load_data()
        return True, btc_amount

    def load_data(self):
        if os.path.exists('bittrex_data_h5.h5'):
            print("reading h5 file... ")
            try:
                temp_markets = h5py.File("bittrex_data_h5.h5", 'r')
                markets = {}
                for k in temp_markets.keys():
                    markets[k] = list(temp_markets[k])
                self.prices = markets
            except Exception as e:
                logging.error(f'[ERROR] reading h5 file... populating dic {e}')
                self.populate()
        else:
            print("no h5 file found... populating dictionary...")
            logging.warning('[ERROR] reading h5 file... populating dic')
            self.populate()

    def populate(self):
        """Populate prices dictionary with markets trading on Bittrex"""

        endpoint = "https://bittrex.com/api/v1.1/public/getmarketsummaries"
        self.prices = {'TIME': [time.time()]}

        try:
            markets = requests.get(endpoint).json()["result"]
            for market in markets:
                symbol = str(market["MarketName"])
                bid = market["Bid"]
                ask = market["Ask"]
                vol = market["Volume"]
                if symbol in self.ignore or symbol[:3] != "BTC":
                    pass
                else:
                    self.prices[symbol] = [(bid, ask, vol)]
        except Exception as e:
            logging.error(f'Failed to get markets from: {e}')
            raise Exception('Failed to get markets from', e)

    @staticmethod
    def get_response(url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'}
        '''faking a user agent here... not sure if that is really useful..'''
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_price(self, pair):
        ''' returns top buy and top sell entry of the orderbook for the pair'''
        buy = None
        sell = None
        while buy == None and sell == None:
            try:
                TICKER_URL = 'https://bittrex.com/api/v1.1/public/getorderbook?market={}&type=sell'.format(pair)
                data = self.get_response(TICKER_URL)
                sell = float(data['result'][0]['Rate'])
                TICKER_URL = 'https://bittrex.com/api/v1.1/public/getorderbook?market={}&type=buy'.format(pair)
                data = self.get_response(TICKER_URL)
                buy = float(data['result'][0]['Rate'])
            except Exception as e:
                print(e)
                print(traceback.format_exc())
                time.sleep(2)
        return buy, sell

    def get_prices(self):
        """updates prices dictionary with markets trading on Bittrex"""
        if len(self.prices['TIME']) > self.MAX_MEM:
            ''' to prevent data/memory overflow '''
            shorten = True
        else:
            shorten = False
        endpoint = "https://bittrex.com/api/v1.1/public/getmarketsummaries"
        try:
            markets = requests.get(endpoint).json()["result"]
            for market in markets:
                symbol = str(market["MarketName"])
                bid = market["Bid"]  # buy
                ask = market["Ask"]  # sell
                vol = market["Volume"]  # volume
                if symbol in self.prices:
                    if shorten:
                        ''' to prevent data overflow '''
                        self.prices[symbol] = self.prices[symbol][-self.MAX_MEM:]
                    self.prices[symbol].append((bid, ask, vol))
            if shorten:
                self.prices['TIME'] = self.prices['TIME'][-self.MAX_MEM:]
            self.prices['TIME'].append(time.time())
            # only main and 0 threads are allowed to write to the file (avoid collisions)
            logging.info("deleting old, creating new old file")
            os.system(" rm -f bittrex_data_h5_old.h5 ")
            os.system(" mv bittrex_data_h5.h5 bittrex_data_h5_old.h5 ")
            h = h5py.File('bittrex_data_h5.h5', 'w')
            for k, v in self.prices.items():
                h.create_dataset(k, data=np.array(v))
            h.close()

        except Exception as e:
            print('Failed to get markets from', e)
            logging.warning(f"prices update failed {e}")
            time.sleep(30)
            return self.prices

    def buy(self, pair):
        '''returns True if succesful, else False'''
        my_bittrex = Bittrex(self.__API_KEY, self.__API_SECRET)
        while True:
            self.wallet = my_bittrex.get_balance('BTC')
            price = self.get_price(pair)[1]
            btc_amount = wallet['result']['Available']
            if btc_amount > self.stake:
                btc_amount = self.stake
            else:
                logging.info('stake is {}, only {} available, quitting THREAD'.format(self.stake, btc_amount))
                exit()
            ret = my_bittrex.buy_limit(pair, 0.99 * (btc_amount / float(price)), price)
            if str(ret['success']) == 'True':
                logging.info("BUYING {} BTC in {}".format(btc_amount, pair), ret)
                UUID = str(ret['result']['uuid'])
                time.sleep(2)
                while True:
                    open_orders = my_bittrex.get_open_orders(pair)
                    if UUID in open_orders['result']:
                        ret = my_bittrex.cancel(UUID)
                        logging.info('BUY ORDER CANCELLED, UUID: {}'.format(UUID), ret)
                        time.sleep(0.5)
                        wallet = my_bittrex.get_balance('BTC')
                        btc_amount = wallet['result']['Available']
                        break
                    else:
                        logging.info('BUY ORDER CONFIRMED', 'UUID: {}'.format(UUID))
                        return True
            else:
                logging.error('ERROR: BUY ORDER FAILED: {}'.format(pair), ret)
                return False

    def sell(self, pair):
        '''returns True if succesful, else False'''
        my_bittrex = Bittrex(self.__API_KEY, self.__API_SECRET)
        while True:
            wallet = my_bittrex.get_balance(pair.replace('BTC-', ''))
            price = self.get_price(pair)[0]
            coin_amount = wallet['result']['Available']
            ret = my_bittrex.sell_limit(pair, COIN_AMOUNT, price)
            if str(ret['success']) == 'True':
                logging.info(
                    "SELLING {} {} for {} BTC".format(COIN_AMOUNT, pair.replace('BTC-', ''), COIN_AMOUNT * price),
                    ret)
                UUID = str(ret['result']['uuid'])
                time.sleep(2)
                while True:
                    open_orders = my_bittrex.get_open_orders(pair)
                    if UUID in open_orders['result']:
                        ret = my_bittrex.cancel(UUID)
                        logging.info('SELL ORDER CANCELLED, UUID: {}'.format(UUID), ret)
                        time.sleep(0.5)
                        wallet = my_bittrex.get_balance(pair.replace('BTC-', ''))
                        coin_amount = wallet['result']['Available']
                        break
                    else:
                        logging.info('SELL ORDER CONFIRMED', 'UUID: {}'.format(UUID))
                        self.stake = coin_amount * price * 0.99
                        return True
            else:
                logging.error('ERROR: SELL ORDER FAILED: {}'.format(pair), ret)
                return False


if __name__ == "__main__":
    bittrex_exchange = Bittrex_wrapper()
    bittrex_exchange.initial_setup()
    bittrex_exchange.get_prices()
    print(bittrex_exchange.prices)
