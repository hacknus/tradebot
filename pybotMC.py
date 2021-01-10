#!/usr/bin/env python
DISCLAIMER = "\n!!! [ATTENTION]: This BOT works only in python 2.7 and on BITTREX! It trades with all currencies available on BITTREX, except those put in the ignore list...\n It is intended for educational purposes \nand the creator does not claim responsability for any losses.\n Cryptos are a high risk investment.\n DO NOT INVEST MORE THAN YOU ARE PREPARED TO LOOSE!\n"
print(DISCLAIMER)

'''
REQUIREMENTS:

sudo apt-get update
sudo apt-get install python-pip
pip install python-bittrex
pip install numpy
sudo apt-get install python-h5py
'''

import sys
sys.stdout.write("importing... ")
sys.stdout.flush()

import multiprocessing as mp
import traceback 				#for log purposes
import requests
import time
import os
import json
import h5py
import csv
import numpy as np 				#to calculate slope of global market cap
from ast import literal_eval	#to read the price-tuples from the csv file
try:
	from bittrex import Bittrex
except:
	raise Exception("IMPORT ERROR: module bittrex not found, please download from git: https://github.com/ericsomdahl/python-bittrex")

sys.stdout.write("done! \n")
sys.stdout.flush()


def RSI(price,n=200):
	p = [(i[0]+i[1])/2. for i in price]
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
		rsi = s_up/(s_up + s_down)

	return rsi

class MAV:
	'''define moving average'''
	def __init__(self, width, num):
		self.width = width
		self.num = num
		self.upband = [np.nan,np.nan,np.nan]
		self.lowband = [np.nan,np.nan,np.nan]
		self.mav = [np.nan,np.nan,np.nan]
	
	def add(self,price=None):
		'''
		computes the moving averages,
		but only the last three entries 
		for memory saving purposes
		'''
		if price == None:
			self.upband = [np.nan,np.nan,np.nan]
			self.lowband = [np.nan,np.nan,np.nan]
			self.mav = [np.nan,np.nan,np.nan]
		else:
			self.upband = []
			self.lowband = []
			self.mav = []
			p = [(i[0]+i[1])/2. for i in price]
			for y in [ p[:-2],p[:-1],p]:
				'''compute average'''
				s = sum(y[-self.width:])
				av = (s/float(self.width))
				s = 0
				'''compute standard deviation'''
				for j in range(1,self.width+1):
					s+=(y[-j]-av)**2
				std = np.sqrt(s/(self.width-1))
				'''create upper and lower bands'''
				u = av + (std*self.num)
				l = av - (std*self.num)
				self.lowband.append(l)
				self.upband.append(u)
				self.mav.append(av)
					
class Exchange(Bittrex):
	'''adapted API functions'''
	def __init__(self,logname,THREAD_ID):
		'''read API keys'''
		self.logname = logname
		self.THREAD_ID = THREAD_ID
		self.ignore = ["BTC-PKB","BTC-ADA","BTC-RISE","BTC-STRAT","BTC-XVG","BTC-ENG","BTC-FAIR","BTC-VTC","BTC-RISE","BTC-VIA"]
		'''
		print "\n currently not monitoring/trading these pairs:"
		for i in self.ignore:
			print i
		print "for changes: edit self.ignore list in Exchange class \n"
		'''
		self.log("not monitoring/trading following pairs:",str(self.ignore))
		
		try:
			file = open('keys/bittrex_key.txt','r')
			data = file.readlines() 
			self.__API_KEY = data[0].replace('\n','')
			self.__API_SECRET = data[1].replace('\n','')
			file.close()
		except:
			self.log('ERROR: no "bittrex_key.txt" found, exiting...','')
			raise Exception('ERROR: no "bittrex_key.txt" found')
		self.prices = {}
		self.MAX_MEM = 7*60*60*24

	
	def initial_setup(self,lbs):
		if lbs == False:
			my_bittrex = Bittrex(self.__API_KEY, self.__API_SECRET)
			print "got connection"
			wallet =  my_bittrex.get_balances()['result']
			print "got wallets"
			for w in wallet:
				pair = 'BTC-' + str(w['Currency'])
				print pair
				if pair in self.prices and pair not in self.ignore:
					amount = w['Available']
					if amount > 0.0001:
						print "found balance in {} -- selling to BTC!".format(pair)
						if not self.sell(pair):
							print "selling {} failed.. continue anyway... check log file for more info".format(pair)
				else:
					pass
			print "ok --"
			print "checking BTC wallet"
			BTC_amount = my_bittrex.get_balance('BTC')['result']['Available']
			print "ok... {} BTC available to trade".format(BTC_amount)
			self.log("starting trading with {} BTC available, monitoring {} currency pairs on BITTREX".format(BTC_amount, len(self.prices)-2),'')
			print "starting logging/trading"
			return True,BTC_amount
		else:
			eff_lbs = []
			for lb in lbs:
				if lb == '' or lb == None:
					eff_lbs.append('')
					continue
				my_bittrex = Bittrex(self.__API_KEY, self.__API_SECRET)
				print "checking coin wallet"
				COIN_amount = my_bittrex.get_balance(lb.replace('BTC-',''))['result']['Available']
				if COIN_amount < 0.0001:
					eff_lbs.append('')
					self.log("THREAD {} starting trading with {} BTC available, monitoring {} currency pairs on BITTREX".format(lbs.index(lb),BTC_amount, len(self.prices)-2),'-- only {} {} available'.format(COIN_amount,lb.replace('BTC-','')))
				else:
					eff_lbs.append(lb)
					self.log("THREAD {} starting trading with {} {} available, monitoring {} currency pairs on BITTREX".format(lbs.index(lb),COIN_amount,lb.replace('BTC-',''), len(self.prices)-2),'waiting to sell {} '.format(lb))
				print "starting logging/trading"
			BTC_amount = my_bittrex.get_balance('BTC')['result']['Available']
			return eff_lbs,BTC_amount
			
	def setup(self,initial_stake,DIC):
		self.stake = initial_stake
		self.prices = DIC


	def buy(self,pair):
		'''returns True if succesful, else False'''
		my_bittrex = Bittrex(self.__API_KEY, self.__API_SECRET)
		while True:
			wallet =  my_bittrex.get_balance('BTC')
			price = self.get_price(pair)[1]
			BTC_AMOUNT = wallet['result']['Available']
			if BTC_AMOUNT > self.stake:
				BTC_AMOUNT = self.stake
			else:
				self.log('stake is {}, only {} available, quitting THREAD {}'.format(self.stake,BTC_AMOUNT,THREAD_ID),'')
				exit()
			ret = my_bittrex.buy_limit(pair,0.99*(BTC_AMOUNT/float(price)),price)
			if str(ret['success']) == 'True':
				self.log("BUYING {} BTC in {}".format(BTC_AMOUNT,pair),ret)
				UUID = str(ret['result']['uuid'])
				time.sleep(2)
				while True:
					openORDERS = my_bittrex.get_open_orders(pair)
					if UUID in openORDERS['result']:
						ret = my_bittrex.cancel(UUID)
						self.log('BUY ORDER CANCELLED, UUID: {}'.format(UUID),ret)
						time.sleep(0.5)
						wallet =  my_bittrex.get_balance('BTC')
						BTC_AMOUNT = wallet['result']['Available']
						break
					else:
						self.log('BUY ORDER CONFIRMED','UUID: {}'.format(UUID))
						return True			
			else:
				self.log('ERROR: BUY ORDER FAILED: {}'.format(pair),ret)
				return False
	
	def sell(self,pair):
		'''returns True if succesful, else False'''
		my_bittrex = Bittrex(self.__API_KEY, self.__API_SECRET)
		while True:
			wallet =  my_bittrex.get_balance(pair.replace('BTC-',''))
			price = self.get_price(pair)[0]
			COIN_AMOUNT = wallet['result']['Available']
			ret = my_bittrex.sell_limit(pair,COIN_AMOUNT,price)
			if str(ret['success']) == 'True':
				self.log("SELLING {} {} for {} BTC".format(COIN_AMOUNT,pair.replace('BTC-',''),COIN_AMOUNT*price),ret)
				UUID = str(ret['result']['uuid'])
				time.sleep(2)
				while True:
					openORDERS = my_bittrex.get_open_orders(pair)
					if UUID in openORDERS['result']:
						ret = my_bittrex.cancel(UUID)
						self.log('SELL ORDER CANCELLED, UUID: {}'.format(UUID),ret)
						time.sleep(0.5)
						wallet =  my_bittrex.get_balance(pair.replace('BTC-',''))
						COIN_AMOUNT = wallet['result']['Available']
						break
					else:
						self.log('SELL ORDER CONFIRMED','UUID: {}'.format(UUID))
						self.stake = COIN_AMOUNT*price*0.99
						return True			
			else:
				self.log('ERROR: SELL ORDER FAILED: {}'.format(pair),ret)
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
				print e
				print traceback.format_exc()
				time.sleep(2)
		return ret
	
	def get_response(self,url):
		headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'}
		'''faking a user agent here... not sure if that is really useful..''' 
		response = requests.get(url,headers=headers)
		response.raise_for_status()
		return response.json()
	
	def get_price(self,pair):
		''' returns top buy and top sell entry of the orderbook for the pair'''
		buy = None
		sell = None
		while buy == None and sell == None:
			try:
				TICKER_URL = 'https://bittrex.com/api/v1.1/public/getorderbook?market={}&type=sell'.format(pair)
				data = self.get_response(TICKER_URL)
				sell =  float(data['result'][0]['Rate'])
				TICKER_URL = 'https://bittrex.com/api/v1.1/public/getorderbook?market={}&type=buy'.format(pair)		
				data = self.get_response(TICKER_URL)
				buy =  float(data['result'][0]['Rate'])
			except Exception as e:
				print e
				print traceback.format_exc()
				time.sleep(2)
		return buy,sell
	
	def populate(self):
		"""Populate prices dictionary with markets trading on Bittrex"""
			
		endpoint = "https://bittrex.com/api/v1.1/public/getmarketsummaries"
		self.prices = {'TIME' : [time.time()], 'GLOBAL' : [self.get_global()] }
		
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
					self.prices[symbol] = [(BID,ASK,VOL)]
		except Exception as e:
			raise Exception('Failed to get markets from',e)	
			
	def get_prices(self):
		"""updates prices dictionary with markets trading on Bittrex"""
		#self.MAX_MEM = 7*60*60*24
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
				BID = market["Bid"] 		#buy
				ASK = market["Ask"] 		#sell
				VOL = market["Volume"]		#volume
				if symbol in self.prices:
					if shorten:
						''' to prevent data overflow '''
						self.prices[symbol] = self.prices[symbol][-self.MAX_MEM:]
					self.prices[symbol].append((BID,ASK,VOL))
			if shorten:
				self.prices['TIME'] = self.prices['TIME'][-self.MAX_MEM:]
				self.prices['GLOBAL'] = self.prices['GLOBAL'][-self.MAX_MEM:]
			self.prices['TIME'].append(time.time())
			self.prices['GLOBAL'].append(self.get_global())
			if not self.THREAD_ID or self.THREAD_ID == 0:
			
				# only main and 0 threads are allowed to write to the file (avoid collisions)
				print "deleting old, creating new old file"
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
			print('Failed to get markets from',e)
			self.log("prices update failed",e)
			time.sleep(30)
			return self.prices


	def log(self,e,tr):
		''' log entry '''
		with open("{}_log.csv".format(self.logname), 'a') as fp:
			a = csv.writer(fp, delimiter=',')
			a.writerow([time.ctime(),e,tr])
		return "logged"



	




def buy_condition(longmav,shortmav):
	if shortmav.mav[-3] < longmav.mav[-3] and shortmav.mav[-2] < longmav.mav[-2] and shortmav.mav[-1] > longmav.mav[-1]:
		return True
	else:
		return False


def sell_condition(longmav,shortmav,lastbuy):
	STOPLOSS_THRESHOLD = 0.
	if os.path.exists('configMC.txt'):
		try:
			file = open('configMC.txt','r')
			config = file.readline()
			file.close()
			STOPLOSS_THRESHOLD = int(config[0])
		except Exception as e:
			B.log('[ERROR] reading configMC.txt',e)
	if shortmav.mav[-1] > lastbuy*1.05:
		return True
	elif shortmav.mav[-1] < lastbuy*STOPLOSS_THRESHOLD:
		B.log('STOP LOSS, lost more than {}%'.format((1-STOPLOSS_THRESHOLD)*100,''))
		return True
	else:
		return False

def make_MAV(MAV):
	#MAV length
	HH_MAV = MAV(B.MAX_MEM/2,3)
	M_MAV = MAV(10,3)
	
	return HH_MAV,M_MAV


def main(THREAD_ID,q,already_bought,initial_stake,DIC):
	''' setup '''
	B = Exchange('pybotMC_{}'.format(THREAD_ID),THREAD_ID)
	
	'''setting initial_stake'''
	B.setup(initial_stake,DIC)
	
	BOUGHT = already_bought
	
	if BOUGHT:
		lastbuy = B.get_price(BOUGHT)[1]
		B.log("THREAD {} starting trading with {}, monitoring {} currency pairs on BITTREX".format(THREAD_ID,BOUGHT.replace('BTC-',''), len(B.prices)-2),'waiting to sell {} '.format(BOUGHT))
	else:
		lastbuy = None
		B.log("THREAD {} starting trading with {} BTC available, monitoring {} currency pairs on BITTREX".format(THREAD_ID,initial_stake, len(B.prices)-2),'')

	

	'''create MAVS'''
	
	# doing this using a function may help later to create a programm that changes its MAV length depending on the market
	HH_MAV,M_MAV = make_MAV(MAV)
	
	print "STARTING... THREAD-ID: ",THREAD_ID
	B.log('LAUNCHING THREAD-ID: {}'.format(THREAD_ID),'PID = {}'.format(os.getpid()))

	WAIT_TIME = 60*60*2 #seconds to wait between measurements
	
	while True:
		try:
			time.sleep(WAIT_TIME)
			B.get_prices() 			#updates dictionary/csv
			if len(B.prices["TIME"]) <= HH_MAV.width:
				continue
			else:
				pass
			#m,c = np.polyfit(B.prices["TIME"],B.prices["GLOBAL"],1)
			m = 1
			c = 1
			for market in B.prices:
				if market == "TIME" or market == "GLOBAL":
					continue
				HH_MAV.add(B.prices[market])
				M_MAV.add(B.prices[market])
				with open("pybotMC_threadbuys.csv",'r') as csvfile:
					readCSV = csv.reader(csvfile, delimiter=',')
					THREAD_BUYS = ''
					for out in readCSV:
						THREAD_BUYS = out

				if market not in THREAD_BUYS and buy_condition(HH_MAV,M_MAV) and m > 0 and BOUGHT == None:
					if B.buy(market):
						lastbuy = B.prices[market][-1][0]
						BOUGHT = market
						q.put(['buying',market,i])
					else:
						pass
				while BOUGHT != None:
					time.sleep(WAIT_TIME)
					B.get_prices()		#updates dictionary/csv
					HH_MAV.add(B.prices[BOUGHT])
					M_MAV.add(B.prices[BOUGHT])
					if sell_condition(HH_MAV,M_MAV,lastbuy):
						if B.sell(market):
							BOUGHT = None
							lastbuy = None
							q.put(['selling',market,i])
							break
						else:
							pass
		except Exception as e:
			B.log(e,traceback.format_exc())
			print "ERROR OCCURRED - logged: ",e

def queue_writer(B,q):
	
	while True:
		try:
			item = q.get()
			if len(item) != 3:
				print "invalid item in queue: {}".format(item)
				print "skipping"
				B.log( "invalid item in queue: {}".format(item),'skipping')
				continue
			i = item[2]			
			with open("pybotMC_threadbuys.csv",'r') as csvfile:
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
			B.log('ERROR in queue - continueing: {}'.format(e),traceback.format_exc())
			print "ERROR OCCURRED - logged: ",e
		


if __name__ == '__main__':



	NUM_COINS = 7 #number of coins to be tracked simultaneously




	B = Exchange('pybotMC_MAIN',None)
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
			B.log('[ERROR] reading h5 file... populating dic',e)
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
			with open("pybotMC_threadbuys.csv",'r') as csvfile:
				readCSV = csv.reader(csvfile, delimiter=',')
				for out in readCSV:
					THREAD_BUYS = out
	
	
	'''checking for full wallets:''' 
	print "checking wallets..."
	ret, AMOUNT = B.initial_setup(THREAD_BUYS)
	print "checked"

	if ret == True:
		'''starting trading with BTC'''
		THREAD_BUYS = None
		eff_NUM_COINS = NUM_COINS
	else:
		'''waiting to sell an already bought coin, then trading BTC'''
		THREAD_BUYS = ret
		eff_NUM_COINS = THREAD_BUYS.count('')

	if eff_NUM_COINS != 0:
		initial_stake = AMOUNT/eff_NUM_COINS
		if initial_stake < 0.001:
			print "only {} BTC available as initial stake, exiting...".format(initial_stake)
			B.log("only {} BTC available as initial stake, exiting...".format(initial_stake),'')
			exit()
	else:
		initial_stake = None
		B.log(' CAUTION --NO initial stake given','launching threads with previously bought coins')

		
	print 'launching threads in ...'
	
	#leaving some time between population of prices-dic by main thread and adding prices by thread 0
	for countdown in range(3,0,-1):
		print countdown
		time.sleep(1)
		
		
	B.log("LAUNCHING THREADS ",'MAIN PID = {}'.format(os.getpid()))
	
	
	jobs = []
	out = []
	q = mp.Queue()

	if THREAD_BUYS:
		if NUM_COINS != len(THREAD_BUYS):
			B.log("NUM_COINS != THREAD_BUYS",'exiting')
			exit() 
	for i in range(NUM_COINS):
		if THREAD_BUYS:
			print THREAD_BUYS[i]
		if THREAD_BUYS:
			if THREAD_BUYS[i] != '':
				THREAD_BUY = THREAD_BUYS[i]
			else:
				THREAD_BUY = None
		else:
			THREAD_BUY = None
			
		#launch processes
		
		p = mp.Process(target=main, args=(i,q,THREAD_BUY,initial_stake,B.prices))
		jobs.append(p)
		p.start()
		out.append('')
		time.sleep(1) 		# to ensure the bots are not run in sync and buy at the same time
	
	p = mp.Process(target=queue_writer, args=(B,q))
	jobs.append(p)
	p.start()

	try:

		while True:
			for i in range(NUM_COINS):
				if not jobs[i].is_alive():
					#B.log('THREAD {} CRASHED'.format(i), 'RESTARTING')
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
				
					#launch processes
			
					p = mp.Process(target=main, args=(i,q,THREAD_BUY,initial_stake,B.prices))
					jobs[i] = p
					p.start()
					B.log('THREAD {} RESTARTET'.format(i),'')
					time.sleep(1) 
					
			time.sleep(20) #dont make it so cpu intensive
	

	except Exception as e:
		B.log('FATAL ERROR: {} ---- CLOSING ALL THREADS, nosell'.format(e),traceback.format_exc())
		print "ERROR OCCURRED - logged: ",e
		for p in jobs:
			p.terminate()
			p.join()

