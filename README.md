# python crypto tradebot
A tradebot for cryptocurrencies.
pybotMC.py spawns multiple threads, each monitoring an altcoin on Bittrex. buy and sell are described by the
sell_condition and buy_condition functions. (<b>attention</b> this is old, outdated code, please refer to the bittrex_exchange.py for an interface to bittrex, it's a handler for the python-bittrex library)
API keys should be stored in the /keys folder, which is ignored by git, such that they will never be made public.
Example: 
./keys/bittrex_key.txt
should cointain the API key and API secret (two lines)<br/><br/>

python-bittrex library can be used to access bittrex exchange.<br/>
bittrex_exchange.py is a wrapper for this library <br/>
compare_bot.py is a template to compare the bitcoin prices on different exchanges <br/>
TestFramework.py should be the test framework where one can train/observe the bot with old data <br/>
<br/>
coin.py is a cointainer class for a currency <br/>
mav.py is a moving average class - could be replaced by pandas <br/>
plot.py shows the data <br/>
<br/>
old data is not included in the git (size) but can be downloaded from http://www.cryptodatadownload.com
