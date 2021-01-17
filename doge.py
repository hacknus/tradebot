from bittrex import Bittrex
import numpy as np
import time
import requests
import logging
import traceback
import os
import h5py


def init():
    try:
        file = open('keys/bittrex_key.txt', 'r')

        data = file.readlines()
        __API_KEY = data[0].replace('\n', '')
        __API_SECRET = data[1].replace('\n', '')
        file.close()
    except FileNotFoundError:
        logging.error('ERROR: no "bittrex_key.txt" found, exiting...', '')
        raise Exception('ERROR: no "bittrex_key.txt" found')
    return Bittrex(__API_KEY, __API_SECRET)


if __name__ == "__main__":
    my_bittrex = init()
    order = my_bittrex.get_order("52ccd861-d889-4922-a4a9-2c1bd644b9ab")
    print(order)
    orders = my_bittrex.get_open_orders("BTC-DOGE")
    print(orders)
    wallet = my_bittrex.get_balance("BTC")
    print(wallet)
    wallet = my_bittrex.get_balance("DOGE")
    print(wallet)
    exit()
    r = my_bittrex.get_market_history('BTC-DOGE')
    for res in r['result']:
        print(res)
    r = my_bittrex.buy_limit("BTC-DOGE", "5000", 2.5e-7)
    print(r)
