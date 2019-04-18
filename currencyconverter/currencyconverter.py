import irc3
from irc3.plugins.command import command

import re
import requests


@irc3.plugin
class CurrencyConverterIRC3:

    def __init__(self, bot):

        self.bot = bot
        self.url = "https://api.exchangeratesapi.io/latest"

        self.currencies = self.available_currencies()

    @command
    def currency(self, mask, target, args):
        """Convert from one currency to another

           %%currency <from> <to>
        """

        base_amount = 0
        currencies = {
            "base": None,
            "symbols": None
        }

        pattern = "^(\d.*\d)(\w+)$"
        m = re.match(pattern, args["<from>"], re.IGNORECASE)
        if m:
            base_amount = m.group(1)
            currencies["base"] = m.group(2).upper()

            if currencies["base"] not in self.currencies:
                return "Please put both base and new currency"
        else:
            return "Please check you syntax"

        if args["<to>"].upper() in self.currencies:
            currencies["symbols"] = args["<to>"].upper()
        else:
            return "Please put both base and new currency"

        data = self.request_api(params=currencies)
        if not data:
            return None

        converted_amount = round(float(base_amount) * data["rates"][currencies["symbols"]], 2)

        output = "{base_amount} {base_symbol} = {converted_amount} {converted_symbol}".format(
            base_amount = base_amount,
            base_symbol = currencies["base"],
            converted_amount = converted_amount,
            converted_symbol = currencies["symbols"]
        )

        return output

    @command
    def currencylist(self, mask, target, args):
        """List avaiable currencies for conversion

           %%currencylist
        """
        return ", ".join(self.currencies)

    def available_currencies(self):

        currencies = []

        data = self.request_api()
        if not data:
            return False

        currencies.append(data["base"])

        for currency in data["rates"].items():
            currencies.append(currency[0])

        return currencies

    def request_api(self, params={}):

        try:
            res = requests.get(self.url, params=params)
            if res.status_code == 200:
                return res.json()
            else:
                pass
        except ConnectionError:
            pass
        print("Unable to connect to API")
        return False
