import irc3
import requests
import re
from bs4 import BeautifulSoup
from irc3.plugins.command import command


@irc3.plugin
class CurrencyConverterIRC3:

    def __init__(self, bot):
        self.bot = bot
        self.url = "https://finance.google.com/finance/converter"
        self.currencies = self.availableCurrencies()

    # @irc3.event(irc3.rfc.PRIVMSG)
    # def youtube(self, mask=None, event=None, target=None, data=None, **kw):
    #     match = None
    #     pattern = ".+(?:youtube\.com\/(?:watch\?v=|v\/)|youtu\.be\/)([\w-]+)"
    #     match = re.match(pattern, data, re.IGNORECASE)
    #     if match:
    #         res = requests.get("https://www.youtube.com/watch?v={}".format(match.group(1)))

    #         soup = BeautifulSoup(res.text, "html.parser")

    #         self.bot.privmsg(
    #             target,
    #             soup.title.string
    #         )

    @command(options_first=True)
    def currency(self, mask, target, args):
        """Convert from one currency to another

            %%currency <from> <to>
        """

        amount = 0
        fromCurrency = None
        toCurrency = None

        for c in self.currencies:
            pattern = "^(-?[\d.]+){}$".format(c[0])
            m = re.match(pattern, args["<from>"], re.IGNORECASE)
            if m:
                amount = m.group(1)
                fromCurrency = str(c[0])

            if args["<to>"].strip(" ").lower() == c[0]:
                toCurrency = c[0]

            if toCurrency and fromCurrency:
                url = self.url + "?a={}&from={}&to={}".format(
                    amount,
                    fromCurrency,
                    toCurrency
                )
                res = requests.get(url)
                pattern = '.*<span class=bld>(.+)</span>.*'
                total = re.search(pattern, res.text).group(1)
                self.bot.privmsg(
                    target,
                    total
                )
                return

        coins = []
        if toCurrency is None:
            coins.append(args["<to>"].upper())
            
        if fromCurrency is None:
            coins.append(re.match("^-?[\d.]+(.+)$", args["<from>"]).group(1).upper())

        
        if len(coins) > 1:
            output = "{} are invalid currencies."
            output = output.format(" and ".join(coins))
        else:
            output = "{} is an invalid currency".format(coins[0])

        self.bot.privmsg(
            target,
            output
        )

    @command
    def currencylist(self, mask, target, args):
        """Display all avaliable currencies IDs

        %%currencylist
        """
        currencyList = ""
        for c in self.currencies:
            currencyList += c[0] + " "
        
        print(self.currencies)

        self.bot.privmsg(
            target,
            currencyList
        )


    def availableCurrencies(self):
        res = requests.get(self.url)
        soup = BeautifulSoup(res.text, "html.parser")
        options = soup.select('select[name=to] > option')
        currencies = []
        for opt in options:
            pattern = '.*<option value="(.+)">(.+?)\s\(.+</option>.*'
            currency = re.match(pattern, str(opt))

            currencies.append([
                currency.group(1).lower(),
                currency.group(2)
            ])
        return currencies
