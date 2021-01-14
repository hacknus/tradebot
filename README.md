# python crypto tradebot
A tradebot for cryptocurrencies.
pybotMC.py spawns multiple threads, each monitoring an altcoin on Bittrex. buy and sell are described by the
sell_condition and buy_condition functions. (<b>attention</b> this is old, outdated code, please refer to the bittrex_exchange.py for an interface to bittrex, it's a handler for the python-bittrex library)
API keys should be stored in the /keys folder, which is ignored by git, such that they will never be made public.
Example: 
./keys/bittrex_key.txt
should cointain the API key and API secret (two lines)


## method 1:
create a test-set for training, to test buy and sell conditions for altcoins (peak detections) in order to get reliable (>50%) success rate on

## method 2:
implement more exchanges and compare them (pattern recognition). if one exchange is trailing behind another one, buy and sell based on the leading exchange in order to make a profit.
Note: this method is a lot less longterm because exchange-behaviour may likely change in the future.
