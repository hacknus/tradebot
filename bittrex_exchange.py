from bittrex import Bittrex
import csv
import time
import requests


class Bittrex_wrapper(Bittrex):
    '''adapted API functions'''

    def __init__(self, logname, THREAD_ID):
        '''read API keys'''
        self.logname = logname
        self.THREAD_ID = THREAD_ID
        self.ignore = ["BTC-PKB", "BTC-ADA", "BTC-RISE", "BTC-STRAT", "BTC-XVG", "BTC-ENG", "BTC-FAIR", "BTC-VTC",
                       "BTC-RISE", "BTC-VIA"]
        '''
        print "\n currently not monitoring/trading these pairs:"
        for i in self.ignore:
            print i
        print "for changes: edit self.ignore list in Exchange class \n"
        '''
        self.log("not monitoring/trading following pairs:", str(self.ignore))

        try:
            file = open('keys/bittrex_key.txt', 'r')
            data = file.readlines()
            self.__API_KEY = data[0].replace('\n', '')
            self.__API_SECRET = data[1].replace('\n', '')
            file.close()
        except:
            self.log('ERROR: no "bittrex_key.txt" found, exiting...', '')
            raise Exception('ERROR: no "bittrex_key.txt" found')
        self.prices = {}
        self.MAX_MEM = 7 * 60 * 60 * 24

    def initial_setup(self, lbs):
        if lbs == False:
            my_bittrex = Bittrex(self.__API_KEY, self.__API_SECRET)
            print("got connection")
            wallet = my_bittrex.get_balances()['result']
            print("got wallets")
            for w in wallet:
                pair = 'BTC-' + str(w['Currency'])
                print(pair)
                if pair in self.prices and pair not in self.ignore:
                    amount = w['Available']
                    if amount > 0.0001:
                        print("found balance in {} -- selling to BTC!".format(pair))
                        if not self.sell(pair):
                            print("selling {} failed.. continue anyway... check log file for more info".format(pair))
                else:
                    pass
            print("ok --")
            print("checking BTC wallet")
            BTC_amount = my_bittrex.get_balance('BTC')['result']['Available']
            print("ok... {} BTC available to trade".format(BTC_amount))
            self.log(
                "starting trading with {} BTC available, monitoring {} "
                "currency pairs on BITTREX".format(BTC_amount, len(self.prices) - 2),
                '')
            print("starting logging/trading")
            return True, BTC_amount
        else:
            eff_lbs = []
            for lb in lbs:
                if lb == '' or lb == None:
                    eff_lbs.append('')
                    continue
                my_bittrex = Bittrex(self.__API_KEY, self.__API_SECRET)
                print("checking coin wallet")
                COIN_amount = my_bittrex.get_balance(lb.replace('BTC-', ''))['result']['Available']
                if COIN_amount < 0.0001:
                    eff_lbs.append('')
                    self.log(
                        "THREAD {} starting trading with {} BTC available, monitoring {} currency pairs on BITTREX".format(
                            lbs.index(lb), BTC_amount, len(self.prices) - 2),
                        '-- only {} {} available'.format(COIN_amount, lb.replace('BTC-', '')))
                else:
                    eff_lbs.append(lb)
                    self.log(
                        "THREAD {} starting trading with {} {} available, monitoring {} currency pairs on BITTREX".format(
                            lbs.index(lb), COIN_amount, lb.replace('BTC-', ''), len(self.prices) - 2),
                        'waiting to sell {} '.format(lb))
                print("starting logging/trading")
            BTC_amount = my_bittrex.get_balance('BTC')['result']['Available']
            return eff_lbs, BTC_amount

    def setup(self, initial_stake, DIC):
        self.stake = initial_stake
        self.prices = DIC

    def buy(self, pair):
        '''returns True if succesful, else False'''
        my_bittrex = Bittrex(self.__API_KEY, self.__API_SECRET)
        while True:
            wallet = my_bittrex.get_balance('BTC')
            price = self.get_price(pair)[1]
            BTC_AMOUNT = wallet['result']['Available']
            if BTC_AMOUNT > self.stake:
                BTC_AMOUNT = self.stake
            else:
                self.log('stake is {}, only {} available, quitting THREAD {}'.format(self.stake, BTC_AMOUNT, THREAD_ID),
                         '')
                exit()
            ret = my_bittrex.buy_limit(pair, 0.99 * (BTC_AMOUNT / float(price)), price)
            if str(ret['success']) == 'True':
                self.log("BUYING {} BTC in {}".format(BTC_AMOUNT, pair), ret)
                UUID = str(ret['result']['uuid'])
                time.sleep(2)
                while True:
                    openORDERS = my_bittrex.get_open_orders(pair)
                    if UUID in openORDERS['result']:
                        ret = my_bittrex.cancel(UUID)
                        self.log('BUY ORDER CANCELLED, UUID: {}'.format(UUID), ret)
                        time.sleep(0.5)
                        wallet = my_bittrex.get_balance('BTC')
                        BTC_AMOUNT = wallet['result']['Available']
                        break
                    else:
                        self.log('BUY ORDER CONFIRMED', 'UUID: {}'.format(UUID))
                        return True
            else:
                self.log('ERROR: BUY ORDER FAILED: {}'.format(pair), ret)
                return False

    def sell(self, pair):
        '''returns True if succesful, else False'''
        my_bittrex = Bittrex(self.__API_KEY, self.__API_SECRET)
        while True:
            wallet = my_bittrex.get_balance(pair.replace('BTC-', ''))
            price = self.get_price(pair)[0]
            COIN_AMOUNT = wallet['result']['Available']
            ret = my_bittrex.sell_limit(pair, COIN_AMOUNT, price)
            if str(ret['success']) == 'True':
                self.log("SELLING {} {} for {} BTC".format(COIN_AMOUNT, pair.replace('BTC-', ''), COIN_AMOUNT * price),
                         ret)
                UUID = str(ret['result']['uuid'])
                time.sleep(2)
                while True:
                    openORDERS = my_bittrex.get_open_orders(pair)
                    if UUID in openORDERS['result']:
                        ret = my_bittrex.cancel(UUID)
                        self.log('SELL ORDER CANCELLED, UUID: {}'.format(UUID), ret)
                        time.sleep(0.5)
                        wallet = my_bittrex.get_balance(pair.replace('BTC-', ''))
                        COIN_AMOUNT = wallet['result']['Available']
                        break
                    else:
                        self.log('SELL ORDER CONFIRMED', 'UUID: {}'.format(UUID))
                        self.stake = COIN_AMOUNT * price * 0.99
                        return True
            else:
                self.log('ERROR: SELL ORDER FAILED: {}'.format(pair), ret)
                return False

    def get_global(self):
        TICKER_URL = "https://api.coinmarketcap.com/v1/global/"
        ret = None
        return 0
        while ret == None:
            try:
                data = self.get_response(TICKER_URL)
                ret = data['total_market_cap_usd']
            except Exception as e:
                print(e)
                print(traceback.format_exc())
                time.sleep(2)
        return ret

    def get_response(self, url):
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

    def populate(self):
        """Populate prices dictionary with markets trading on Bittrex"""

        endpoint = "https://bittrex.com/api/v1.1/public/getmarketsummaries"
        self.prices = {'TIME': [time.time()], 'GLOBAL': [self.get_global()]}

        try:
            markets = requests.get(endpoint).json()["result"]
            for market in markets:
                symbol = str(market["MarketName"])
                BID = market["Bid"]
                ASK = market["Ask"]
                VOL = market["Volume"]
                if symbol in self.ignore or symbol[:3] != "BTC":
                    pass
                else:
                    self.prices[symbol] = [(BID, ASK, VOL)]
        except Exception as e:
            raise Exception('Failed to get markets from', e)

    def get_prices(self):
        """updates prices dictionary with markets trading on Bittrex"""
        # self.MAX_MEM = 7*60*60*24
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
                BID = market["Bid"]  # buy
                ASK = market["Ask"]  # sell
                VOL = market["Volume"]  # volume
                if symbol in self.prices:
                    if shorten:
                        ''' to prevent data overflow '''
                        self.prices[symbol] = self.prices[symbol][-self.MAX_MEM:]
                    self.prices[symbol].append((BID, ASK, VOL))
            if shorten:
                self.prices['TIME'] = self.prices['TIME'][-self.MAX_MEM:]
                self.prices['GLOBAL'] = self.prices['GLOBAL'][-self.MAX_MEM:]
            self.prices['TIME'].append(time.time())
            self.prices['GLOBAL'].append(self.get_global())
            if not self.THREAD_ID or self.THREAD_ID == 0:

                # only main and 0 threads are allowed to write to the file (avoid collisions)
                print("deleting old, creating new old file")
                print(os.system(" rm -f pybotMC_data_h5_old.h5 "))
                print(os.system(" mv pybotMC_data_h5.h5 pybotMC_data_h5_old.h5 "))
                h = h5py.File('pybotMC_data_h5.h5', 'w')
                for k, v in self.prices.items():
                    h.create_dataset(k, data=np.array(v))
                h.close()

            # with open('pybotMC_data.csv', "w") as outfile:
            # 	writer = csv.writer(outfile)
            # 	writer.writerow(self.prices.keys())
            # 	writer.writerows(zip(*self.prices.values()))
        except Exception as e:
            print('Failed to get markets from', e)
            self.log("prices update failed", e)
            time.sleep(30)
            return self.prices

    def log(self, e, tr):
        ''' log entry '''
        with open("{}_log.csv".format(self.logname), 'a') as fp:
            a = csv.writer(fp, delimiter=',')
            a.writerow([time.ctime(), e, tr])
        return "logged"
