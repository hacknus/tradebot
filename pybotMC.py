#!/usr/bin/env python
import multiprocessing as mp
import traceback  # for log purposes
import time
import os
import h5py
import csv
import numpy as np  # to calculate slope of global market cap
from bittrex_exchange import Bittrex_wrapper
import sys

DISCLAIMER = "\n!!! [ATTENTION]: It trades with all currencies available on BITTREX, " \
             "except those put in the ignore list...\n It is intended for educational purposes" \
             " \nand the creator does not claim responsability for any losses.\n Cryptos are a high risk" \
             " investment.\n DO NOT INVEST MORE THAN YOU ARE PREPARED TO LOOSE!\n"
print(DISCLAIMER)

sys.stdout.write("done! \n")
sys.stdout.flush()


def RSI(price, n=200):
    p = [(i[0] + i[1]) / 2. for i in price]
    p = np.array(p)
    delta = p[1:] - p[:-1]
    s_up = 0
    s_down = 0
    for i in range(n):
        if delta[-i] > 0:
            s_up += delta[-i]
        elif delta[-i] < 0:
            s_down -= delta[-i]

    if s_up + s_down == 0 or s_up == 0:
        return 0.5
    else:
        rsi = s_up / (s_up + s_down)

    return rsi


class MAV:
    '''define moving average'''

    def __init__(self, width, num):
        self.width = width
        self.num = num
        self.upband = [np.nan, np.nan, np.nan]
        self.lowband = [np.nan, np.nan, np.nan]
        self.mav = [np.nan, np.nan, np.nan]

    def add(self, price=None):
        '''
        computes the moving averages,
        but only the last three entries
        for memory saving purposes
        '''
        if price == None:
            self.upband = [np.nan, np.nan, np.nan]
            self.lowband = [np.nan, np.nan, np.nan]
            self.mav = [np.nan, np.nan, np.nan]
        else:
            self.upband = []
            self.lowband = []
            self.mav = []
            p = [(i[0] + i[1]) / 2. for i in price]
            for y in [p[:-2], p[:-1], p]:
                '''compute average'''
                s = sum(y[-self.width:])
                av = (s / float(self.width))
                s = 0
                '''compute standard deviation'''
                for j in range(1, self.width + 1):
                    s += (y[-j] - av) ** 2
                std = np.sqrt(s / (self.width - 1))
                '''create upper and lower bands'''
                u = av + (std * self.num)
                l = av - (std * self.num)
                self.lowband.append(l)
                self.upband.append(u)
                self.mav.append(av)


def buy_condition(longmav, shortmav):
    if shortmav.mav[-3] < longmav.mav[-3] and shortmav.mav[-2] < longmav.mav[-2] and shortmav.mav[-1] > longmav.mav[-1]:
        return True
    else:
        return False


def sell_condition(longmav, shortmav, lastbuy):
    STOPLOSS_THRESHOLD = 0.
    if os.path.exists('configMC.txt'):
        try:
            file = open('configMC.txt', 'r')
            config = file.readline()
            file.close()
            STOPLOSS_THRESHOLD = int(config[0])
        except Exception as e:
            B.log('[ERROR] reading configMC.txt', e)
    if shortmav.mav[-1] > lastbuy * 1.05:
        return True
    elif shortmav.mav[-1] < lastbuy * STOPLOSS_THRESHOLD:
        B.log('STOP LOSS, lost more than {}%'.format((1 - STOPLOSS_THRESHOLD) * 100, ''))
        return True
    else:
        return False


def make_MAV(MAV):
    # MAV length
    HH_MAV = MAV(B.MAX_MEM / 2, 3)
    M_MAV = MAV(10, 3)

    return HH_MAV, M_MAV


def main(THREAD_ID, q, already_bought, initial_stake, DIC):
    ''' setup '''
    B = Bittrex_wrapper('pybotMC_{}'.format(THREAD_ID), THREAD_ID)

    '''setting initial_stake'''
    B.setup(initial_stake, DIC)

    BOUGHT = already_bought

    if BOUGHT:
        lastbuy = B.get_price(BOUGHT)[1]
        B.log("THREAD {} starting trading with {}, monitoring {} currency pairs on BITTREX".format(THREAD_ID,
                                                                                                   BOUGHT.replace(
                                                                                                       'BTC-', ''),
                                                                                                   len(B.prices) - 2),
              'waiting to sell {} '.format(BOUGHT))
    else:
        lastbuy = None
        B.log("THREAD {} starting trading with {} BTC available, monitoring {} currency pairs on BITTREX".format(
            THREAD_ID, initial_stake, len(B.prices) - 2), '')

    '''create MAVS'''

    # doing this using a function may help later to create a programm that changes its MAV length depending on the market
    HH_MAV, M_MAV = make_MAV(MAV)

    print("STARTING... THREAD-ID: ", THREAD_ID)
    B.log('LAUNCHING THREAD-ID: {}'.format(THREAD_ID), 'PID = {}'.format(os.getpid()))

    WAIT_TIME = 60 * 60 * 2  # seconds to wait between measurements

    while True:
        try:
            time.sleep(WAIT_TIME)
            B.get_prices()  # updates dictionary/csv
            if len(B.prices["TIME"]) <= HH_MAV.width:
                continue
            else:
                pass
            # m,c = np.polyfit(B.prices["TIME"],B.prices["GLOBAL"],1)
            m = 1
            c = 1
            for market in B.prices:
                if market == "TIME" or market == "GLOBAL":
                    continue
                HH_MAV.add(B.prices[market])
                M_MAV.add(B.prices[market])
                with open("pybotMC_threadbuys.csv", 'r') as csvfile:
                    readCSV = csv.reader(csvfile, delimiter=',')
                    THREAD_BUYS = ''
                    for out in readCSV:
                        THREAD_BUYS = out

                if market not in THREAD_BUYS and buy_condition(HH_MAV, M_MAV) and m > 0 and BOUGHT == None:
                    if B.buy(market):
                        lastbuy = B.prices[market][-1][0]
                        BOUGHT = market
                        q.put(['buying', market, i])
                    else:
                        pass
                while BOUGHT != None:
                    time.sleep(WAIT_TIME)
                    B.get_prices()  # updates dictionary/csv
                    HH_MAV.add(B.prices[BOUGHT])
                    M_MAV.add(B.prices[BOUGHT])
                    if sell_condition(HH_MAV, M_MAV, lastbuy):
                        if B.sell(market):
                            BOUGHT = None
                            lastbuy = None
                            q.put(['selling', market, i])
                            break
                        else:
                            pass
        except Exception as e:
            B.log(e, traceback.format_exc())
            print("ERROR OCCURRED - logged: ", e)


def queue_writer(B, q):
    while True:
        try:
            item = q.get()
            if len(item) != 3:
                print("invalid item in queue: {}".format(item))
                print("skipping")
                B.log("invalid item in queue: {}".format(item), 'skipping')
                continue
            i = item[2]
            with open("pybotMC_threadbuys.csv", 'r') as csvfile:
                readCSV = csv.reader(csvfile, delimiter=',')
                THREAD_BUYS = ''
                for out in readCSV:
                    THREAD_BUYS = out

            if item[0] == 'selling':
                THREAD_BUYS[i] = ''
            elif item[0] == 'buying':
                THREAD_BUYS[i] = item[1]

            with open("pybotMC_threadbuys.csv", 'w') as fp:
                a = csv.writer(fp, delimiter=',')
                a.writerow(THREAD_BUYS)

        except Exception as e:
            B.log('ERROR in queue - continueing: {}'.format(e), traceback.format_exc())
            print("ERROR OCCURRED - logged: ", e)


if __name__ == '__main__':

    NUM_COINS = 7  # number of coins to be tracked simultaneously

    B = Bittrex_wrapper('pybotMC_MAIN', None)
    # if not os.path.exists('pybotMC_threadbuys.csv'):
    # 	with open("pybotMC_threadbuys.csv", 'w') as fp:
    # 		a = csv.writer(fp, delimiter=',')
    # 		a.writerow(['' for i in range(NUM_COINS)])
    # if os.path.exists('pybotMC_data.csv'):
    # 	sys.stdout.write("reading csv file... ")
    # 	sys.stdout.flush()
    # 	try:
    # 		reader = csv.DictReader(open('pybotMC_data.csv'))
    # 		markets = {}
    # 		for row in reader:
    # 			for column, value in row.iteritems():
    # 				if type(literal_eval(value)) == float:
    # 					markets.setdefault(column, []).append(float(literal_eval(value)))
    # 				else:
    # 					markets.setdefault(column, []).append((float(literal_eval(value)[0]),float(literal_eval(value)[1]),float(literal_eval(value)[2])))
    # 		B.prices = markets
    # 	except Exception as e:
    # 		log('[ERROR] reading csv file... populating dic',e)
    # 		B.populate()
    # else:
    # 	sys.stdout.write("populating dictionary...")
    # 	sys.stdout.flush()
    # 	B.populate()
    if os.path.exists('pybotMC_data_h5.h5'):
        sys.stdout.write("reading h5 file... ")
        sys.stdout.flush()
        try:
            temp_markets = h5py.File("pybotMC_data_h5.h5", 'r')
            markets = {}
            for k in temp_markets.keys():
                markets[k] = list(temp_markets[k])
            B.prices = markets
        except Exception as e:
            B.log('[ERROR] reading h5 file... populating dic', e)
            B.populate()
    else:
        sys.stdout.write("no h5 file found... populating dictionary...")
        sys.stdout.flush()
        B.populate()

    sys.stdout.write("done! \n")
    sys.stdout.flush()

    THREAD_BUYS = False
    if len(sys.argv) > 1:
        if sys.argv[1] == 'nosell' and os.path.exists('pybotMC_threadbuys.csv'):
            with open("pybotMC_threadbuys.csv", 'r') as csvfile:
                readCSV = csv.reader(csvfile, delimiter=',')
                for out in readCSV:
                    THREAD_BUYS = out

    '''checking for full wallets:'''
    print("checking wallets...")
    ret, AMOUNT = B.initial_setup(THREAD_BUYS)
    print("checked")

    if ret == True:
        '''starting trading with BTC'''
        THREAD_BUYS = None
        eff_NUM_COINS = NUM_COINS
    else:
        '''waiting to sell an already bought coin, then trading BTC'''
        THREAD_BUYS = ret
        eff_NUM_COINS = THREAD_BUYS.count('')

    if eff_NUM_COINS != 0:
        initial_stake = AMOUNT / eff_NUM_COINS
        if initial_stake < 0.001:
            print("only {} BTC available as initial stake, exiting...".format(initial_stake))
            B.log("only {} BTC available as initial stake, exiting...".format(initial_stake), '')
            exit()
    else:
        initial_stake = None
        B.log(' CAUTION --NO initial stake given', 'launching threads with previously bought coins')

    print('launching threads in ...')

    # leaving some time between population of prices-dic by main thread and adding prices by thread 0
    for countdown in range(3, 0, -1):
        print(countdown)
        time.sleep(1)

    B.log("LAUNCHING THREADS ", 'MAIN PID = {}'.format(os.getpid()))

    jobs = []
    out = []
    q = mp.Queue()

    if THREAD_BUYS:
        if NUM_COINS != len(THREAD_BUYS):
            B.log("NUM_COINS != THREAD_BUYS", 'exiting')
            exit()
    for i in range(NUM_COINS):
        if THREAD_BUYS:
            print(THREAD_BUYS[i])
        if THREAD_BUYS:
            if THREAD_BUYS[i] != '':
                THREAD_BUY = THREAD_BUYS[i]
            else:
                THREAD_BUY = None
        else:
            THREAD_BUY = None

        # launch processes

        p = mp.Process(target=main, args=(i, q, THREAD_BUY, initial_stake, B.prices))
        jobs.append(p)
        p.start()
        out.append('')
        time.sleep(1)  # to ensure the bots are not run in sync and buy at the same time

    p = mp.Process(target=queue_writer, args=(B, q))
    jobs.append(p)
    p.start()

    try:

        while True:
            for i in range(NUM_COINS):
                if not jobs[i].is_alive():
                    # B.log('THREAD {} CRASHED'.format(i), 'RESTARTING')
                    B.log('THREAD {} CRASHED'.format(i), 'NOT RESTARTING - exiting all')
                    exit()
                    continue
                    if THREAD_BUYS:
                        if THREAD_BUYS[i] != '':
                            THREAD_BUY = THREAD_BUYS[i]
                        else:
                            THREAD_BUY = None
                    else:
                        THREAD_BUY = None

                    # launch processes

                    p = mp.Process(target=main, args=(i, q, THREAD_BUY, initial_stake, B.prices))
                    jobs[i] = p
                    p.start()
                    B.log('THREAD {} RESTARTET'.format(i), '')
                    time.sleep(1)

            time.sleep(20)  # dont make it so cpu intensive


    except Exception as e:
        B.log('FATAL ERROR: {} ---- CLOSING ALL THREADS, nosell'.format(e), traceback.format_exc())
        print("ERROR OCCURRED - logged: ", e)
        for p in jobs:
            p.terminate()
            p.join()
