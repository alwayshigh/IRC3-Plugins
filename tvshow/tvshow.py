import irc3
from irc3.plugins.command import command
import requests
import re
import datetime


@irc3.plugin
class TvShowInfoIRC3:

    def __init__(self, bot):
        self.bot = bot

    @command(options_first=True)
    def tv(self, mask, target, args):
        """Grab TV Show Info

        %%tv <tvshow>...
        """
        show = " ".join(args["<tvshow>"])

        res = requests.get("http://api.tvmaze.com/singlesearch/shows?q={}".format(show))
    
        if not res.json():
            return
        showInfo = res.json()

        showInfo["genres"] = ", ".join(showInfo["genres"])

        outputLines = []
        outputLines.append("\x0310[ \x0303{name} \x0310] :: [ \x0307Status:\x0F {status} \x0310] :: [ \x0307Genres:\x0F {genres} \x0310]\x0F".format(**showInfo))

        latestEpisode = None
        nextEpisode = None

        try:
            res = requests.get(showInfo["_links"]["previousepisode"]["href"])
            episodeInfo = res.json()
            latestDateInfo = self.dateInfo(episodeInfo["airstamp"])
            latestEpisode = "\x0307Latest Episode:\x0F S{season:02d}E{number:02d} - {name} ( {year} {monthalt} {day} @ {aired}UTC - \x0303{airedOutput} ago\x0F )".format(
                **self.merge_two_dicts(episodeInfo, latestDateInfo))
        except KeyError:
            pass

        if showInfo["status"] != "Ended":
            try:
                res = requests.get(showInfo["_links"]["nextepisode"]["href"])
                episodeInfo = res.json()
                nextDateInfo = self.dateInfo(episodeInfo["airstamp"])
                nextEpisode = "\x0307Next Episode:\x0F S{season:02d}E{number:02d} - {name} ( {year} {monthalt} {day} @ {aired}UTC - \x0303{airedOutput} from now\x0F )".format(
                    **self.merge_two_dicts(episodeInfo, nextDateInfo))
            except KeyError:
                nextEpisode = "\x0307Next Episode:\x0F To Be Announced"
                pass

            if latestEpisode:
                outputLines.append("\x0310[\x0F {} \x0310] :: [\x0F {} \x0310]\x0F".format(latestEpisode, nextEpisode))
            else:
                outputLines.append("\x0310[\x0F {} \x0310]\x0F".format(nextEpisode))
        else:
            outputLines.append("\x0310[\x0F {} \x0310]".format(latestEpisode))

        for output in outputLines:
            self.bot.privmsg(
                target,
                output
            )


    def dateInfo(self, airStamp):
        matches = re.match("(.+)T(.+)\+.*", airStamp)
        airDate = matches.group(1)
        airTime = matches.group(2)

        airStamp = datetime.datetime.strptime(" ".join([airDate, airTime]).strip(" "),
                                              "%Y-%m-%d %H:%M:%S")

        currentDateUTC = datetime.datetime.utcnow()
        if airStamp > currentDateUTC:
            finished = airStamp - currentDateUTC
        else:
            finished = currentDateUTC - airStamp

        days = int(finished.total_seconds() // (60 * 60 * 24))
        hours = int(finished.seconds // (60 * 60))
        mins = int((finished.seconds // 60) % 60)

        aired = ""
        if mins:
            aired = "{}m".format(mins)
        if hours:
            aired = "{}h {}".format(hours, aired)
        if days:
            aired = "{}d {}".format(days, aired)

        date = [int(i) for i in airDate.split("-")]

        return {
            "year": date[0],
            "month": date[1],
            "monthalt": datetime.date(*date).strftime("%b"),
            "day": date[2],
            "aired": airTime,
            "airedOutput": aired
        }


    def merge_two_dicts(self, x, y):
        z = x.copy()
        z.update(y)
        return z
