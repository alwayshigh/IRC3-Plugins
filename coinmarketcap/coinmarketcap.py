#irc3 config.ini > logs/fuckall.log 2>&1 & disown

# -*- coding: utf-8 -*
import irc3
from irc3.plugins.command import command
from irc3.compat import asyncio
from decimal import Decimal
import logging
import json
import random
import re
import requests
import time
import _string

currencyList = {
    "AUD": "${} AUD",
    "BRL": "R${}",
    "CAD": "${} CAD",
    "CHF": "CHF{}",
    "CLP": "${} CLP",
    "CNY": "¥{}",
    "CZK": "{}Kč",
    "DKK": "kr.{}",
    "EUR": "€{}",
    "GBP": "£{}",
    "HKD": "HK${}",
    "HUF": "Ft{}",
    "IDR": "Rp{}",
    "ILS": "₪{}",
    "INR": "₹{}",
    "JPY": "¥{} JPY",
    "KRW": "₩{}",
    "MXN": "${} MXN",
    "MYR": "RM{}",
    "NOK": "kr{}",
    "NZD": "${} NZD",
    "PHP": "₱{}",
    "PKR": "₨{}",
    "PLN": "zł{}",
    "RUB": "₽{}",
    "SEK": "kr{}",
    "SGD": "${} SGD",
    "THB": "฿{}",
    "TRY": "₺{}",
    "TWD": "NT${}",
    "USD": "${}",
    "ZAR": "R{}"
}

@irc3.plugin
class CoinMarketCapIRC3:

    config = {
        "update_timeout": 180,
        "currency_format": "None",
        "default_currency": "USD",
    }

    formats = {
        "coin_net_worth_format": "[{name}] {amount_coin} {symbol} is worth {total_price} | {total_btc} BTC",
        "coin_format": "[{symbol}] {name} - #{rank} | {price_btc} BTC | {price} | 24h Vol - {24h_volume} | 1h {percent_change_1h}% | 24h {percent_change_24h}% | 7d {percent_change_7d}%",
        "top10_format": "[{symbol}] {name} | {percent_change}% | {price_btc} BTC | {price}",
        "volume_format": "[{symbol}] {name} | Vol {24h_volume_percent}% | {price_btc}BTC | {price}",
        "overview_format": "Market Cap: {total_market_cap} | 24h Vol: {total_24h_volume} | BTC Dominance: {bitcoin_percentage_of_market_cap}% | {active_currencies} Currencies / {active_assets} Assets / {active_markets} Markets"
    }

    def __init__(self, bot):
        self.bot = bot
        logging.basicConfig(
            format="[%(asctime)s](%(levelname)s) %(message)s",
            filename=self.bot.config["coinmarketcap"]["log_file"],
            level=logging.INFO
        )

        logging.info("Starting Bot")

        self.config.update(self.bot.config["coinmarketcap"])
        self.formats.update(self.bot.config["coinmarketcap_formats"])
        self.coinMarketCap = CoinMarketCap(self.config)

        self.loop = asyncio.get_event_loop()
        try:
            asyncio.async(self.coinMarketCap.buildCoinData())
        except asyncio.CancelledError:
            pass
        asyncio.async(self.testOutputFormats())
        
    @asyncio.coroutine
    def testOutputFormats(self):
        testFormats = {
            "coin_net_worth_format": ["ticker", ["btc", "1"] ],
            "coin_format": ["ticker", ["btc"] ],
            "top10_format": ["top10", ["gainers", "24h"] ],
            "volume_format": ["volume", None],
            "overview_format": ["overview", None]
        }

        valid = True
        for formatName, data in testFormats.items():
            pass
            if data[1]:
                result = getattr(self.coinMarketCap, data[0])(*data[1])
            else:
                result = getattr(self.coinMarketCap, data[0])()
            
            options = []
            for v in result:
                if not isinstance(v, str):
                    for key, val in enumerate(v):
                        options.append(val)
                    break
                else:
                    options.append(v)

            formatVariables = [fname for _, fname, _, _ in _string.formatter_parser(self.formats[formatName]) if fname]        
            invalids = []
            for var in formatVariables:
                if not var in options:
                    invalids.append(var)

            if invalids:
                invalids = " ".join(["{{{}}}".format(invalids[i]) for i in range(len(invalids))])
                logging.error("Invalid config options: " + formatName + " - " + invalids)
                valid = False

        if not valid:
            print("You have errors in your output formats, Please check logs")
            self.loop.stop()
       

    def printToIRC(self, formatString, values, target):
        try:
            self.bot.privmsg(
                target, 
                self.formats[formatString].format(**values)
            )
        except KeyError as e:
            print(e)    
   
    @command
    def networth(self, mask, target, args):
        """Display total value of amount of coin

            %%networth <amount> <coin>...
        """
        coin = " ".join(args["<coin>"])
        response = self.coinMarketCap.ticker(coin, args["<amount>"])
        if response:
            self.printToIRC("coin_net_worth_format", response, target)             
        else:
            try:
                float(args["<amount>"])

                self.bot.privmsg(
                    target, 
                    "{} - Cant be found.".format(coin)
                )
            except ValueError:
                self.bot.privmsg(
                    target, 
                    "Amount is not a valid number"
                )

    @command
    def coin(self, mask, target, args):
        """Display coin information

            %%coin <coin>...
        """
        coin = " ".join(args["<coin>"])
        response = self.coinMarketCap.ticker(coin)
        if response:
            self.printToIRC("coin_format", response, target)
        else:
            self.bot.privmsg(
                target, 
                "{} - Cant be found.".format(coin)
            )

    @command
    def volume(self, mask, target, args):
        """Display list of top 10 coin trade volumes from past 24 hours

           %%volume
        """
        response = self.coinMarketCap.volume()
        self.bot.privmsg(mask.nick, "Top Trade Volume (24h)")
        for coin in response:
            self.printToIRC("volume_format", coin, target)

    @command
    def overview(self, mask, target, args):
        """Display market overview from the past 24 hours

           %%overview
        """
        response = self.coinMarketCap.overview()
        self.printToIRC("overview_format", response, target)

    @command
    def top10(self, mask, target, args):
        """Display Top 10 Gainers/Losers of a specified time period
           Default: !top10 Will show 24h Gainers

           %%top10 [gainers|losers] [1h|24h|7d]
        """
        timeStamp = "24h"
        option = "gainers"
        for index, value in args.items():
            if index in ["1h","24h","7d"] and value:
                timeStamp = index
            elif index in ["gainers", "losers"] and value:
                option = index

        response = self.coinMarketCap.top10(option, timeStamp)

        self.bot.privmsg(mask.nick, "Top {} ({})".format(option.capitalize(), timeStamp))

        changeIndex = "percent_change_{}".format(timeStamp)
        
        for coin in response:
            coin["percent_change"] = coin[changeIndex]
            self.printToIRC("top10_format", coin, mask.nick)


class CoinMarketCap():
    
    _session = None

    def __init__(self, config):
        logging.info("Initating CoinMarketCap Module")
        self.config = config
        self.coins = {}
        self.topTen = {}

    def __insertCoin(self, dictionary, index, coin, args={}, strip=None):
        dictionary.insert(index, coin)
        if args:
            dictionary[index].update(args)
        if strip and len(dictionary) > strip:
            dictionary = dictionary[:strip]
        return dictionary    

    def __convertCurrency(self, coin, currency):
        updatedCoin = coin.copy()
        for i, c in coin.items():
            if c is None:
                updatedCoin[i] = 0
            if i.endswith(currency.lower()):
                newIndex = re.match(r'(.+)_{}'.format(currency), i, re.IGNORECASE).group(1)
                val = '{:,}'.format(Decimal(updatedCoin[i]))
                updatedCoin[newIndex] = currencyList[currency.upper()].format(val)
        return updatedCoin

    @asyncio.coroutine
    def buildCoinData(self):
        updateTime = time.time()
        defaultCurrency = self.config["default_currency"].upper()

        # Pull market info overview from CoinMarketCap API
        response = self.__convertCurrency(self.__request("global", defaultCurrency), defaultCurrency)
        if response:
            self.marketOverview = response

        # Pull complete coin list from CoinMarketCap API
        response = self.__request("ticker", defaultCurrency)
        if response is None:
            logging.warning("Unable to update coin data, Retrying in {} seconds.").format(self.config["update_timeout"])
            yield from asyncio.sleep(self.config["update_timeout"])
            asyncio.async(self.buildCoinData())

        self.coins = response
        timeStamps = ["1h", "24h", "7d"]
        topTen = {
            "gainers": {
                "1h": [self.coins[0]],
                "24h": [self.coins[0]],
                "7d": [self.coins[0]]
            },
            "losers": {
                "1h": [self.coins[0]],
                "24h": [self.coins[0]],
                "7d": [self.coins[0]]
            },
            "volume": []
        }

        for i, coin in enumerate(self.coins):
            self.coins[i] = coin = self.__convertCurrency(coin, defaultCurrency)

            if coin["id"] != "bitcoin" and coin["price_btc"]:
                self.coins[i]["price_btc"] = coin["price_btc"] = '{:.8f}'.format(float(coin["price_btc"]))

            try:
                #
                ## Build coin top 10 market trade volumes from last 24 hours. 
                #
                volumePercent = round((float(coin["24h_volume_usd"]) / float(self.marketOverview["total_24h_volume_usd"])) * 100, 2)
                if len(topTen["volume"]) != 0:
                    for index, topTenCoin in enumerate(topTen["volume"]):
                        if float(volumePercent) > float(topTenCoin["24h_volume_percent"]):
                            topTen["volume"] = self.__insertCoin(topTen["volume"], index, coin, args={"24h_volume_percent": volumePercent}, strip=10)
                            break
                        elif len(topTen["volume"]) < 10 and index + 1 == len(topTen["volume"]):
                            topTen["volume"] = self.__insertCoin(topTen["volume"], index + 1, coin, args={"24h_volume_percent": volumePercent})
                            break 
                else:
                    topTen["volume"] = self.__insertCoin(topTen["volume"], 0, coin, args={"24h_volume_percent": volumePercent})
            except TypeError:
                # If coin's 24h_volume_usd is None pass iterating it.
                continue

            #
            ## Build coin top 10 gainers & losers over 1 hour, 24 hour and 7 day periods
            #
            for t in timeStamps:
                timeIndex = "percent_change_{}".format(t)
                if coin[timeIndex] is not None and coin["24h_volume_usd"] is not None \
                   and float(coin["24h_volume_usd"]) >= 10000:
                    # Top 10 gainers loop
                    for index, topTenCoin in enumerate(topTen["gainers"][t]):
                        if float(coin[timeIndex]) > float(topTenCoin[timeIndex]):
                            topTen["gainers"][t] = self.__insertCoin(topTen["gainers"][t], index, coin, args={"percent_change": ""}, strip=10)
                            break
                    # Top 10 losers loop
                    for index, topTenCoin in enumerate(topTen["losers"][t]):
                        if float(coin[timeIndex]) < float(topTenCoin[timeIndex]):
                            topTen["losers"][t] = self.__insertCoin(topTen["losers"][t], index, coin, args={"percent_change": ""}, strip=10)
                            break
        self.topTen = topTen
        self.lastUpdated = time.time()
        yield from asyncio.sleep(self.config["update_timeout"])
        asyncio.async(self.buildCoinData())

    def __request(self, option, currency):
        url = "https://api.coinmarketcap.com/v1/{}/?limit=0&convert={}".format(option, currency)
        request = self.session.get(url, timeout=120)
        if request.status_code != 200:
            logging.warning('Unexpected error connecting to ({}). api.coinmarketcap.com might be down?'.format(url))
        else:
            try:
                return request.json()
            except:
                logging.error("Could not parse response as JSON, response code was %s, bad json content was '%s'" % (request.status_code, request.content))
        return None

    @property
    def session(self):
        if not self._session: 
            self._session = requests.Session()
            self._session.headers.update({
                'Content-Type': 'application/json',
                'User-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:55.0) Gecko/20100101 Firefox/55.0'
            })
        return self._session

    def ticker(self, coin, amount=None):
        for c in self.coins:     
            if coin.lower() == c["name"].lower() or coin.lower() == c["symbol"].lower():
                if amount:
                    try:
                        currency = self.config["default_currency"]

                        c["amount_coin"] = amount = float(amount)
                        
                        c["total_btc"] = '{:.8f}'.format(amount * float(c["price_btc"]))
                        c["total_price"] = '{:,}'.format(round(amount * float(c["price_"+currency.lower()]),2))
                        c["total_price"] = currencyList[currency.upper()].format(c["total_price"])
                    except ValueError:
                        return False
                return c
        return False

    def top10(self, options=None, timeStamp=None):
        if not options and not timeStamp:
            return self.topTen
        return self.topTen[options][timeStamp]

    # Return list of top 10 coin trade volumes
    def volume(self):
        return self.topTen["volume"]

    # Return market overview of the past 24 hours
    def overview(self):
        return self.marketOverview

    # Return when last time coin data was last updated in seconds.
    def listLastUpdated(self):
        return "Last Updated:", int(time.time() - self.lastUpdated), "seconds ago."
