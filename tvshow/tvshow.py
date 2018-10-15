import irc3
from irc3.plugins.command import command
import requests
import re
import datetime
import json


@irc3.plugin
class TvShowInfoIRC3:

    def __init__(self, bot):
        self.bot = bot

    @command(options_first=True)
    def tv(self, mask, target, args):
        """Grab TV Show Info

        %%tv <tvshow>...
        """

        show_info = self.get_show(args["<tvshow>"], channel=target)
        if not show_info:
            return

        show_info["genres"] = ", ".join(show_info["genres"])

        output_lines = []
        output_lines.append("\x0310[ \x0303{name} \x0310] :: [ \x0307Status:\x0F {status} \x0310] :: [ \x0307Genres:\x0F {genres} \x0310] :: [\x0F {url} \x0310]\x0F".format(**show_info))

        next_episode = self.build_next_episode(show_info)
        last_episode = self.build_last_episode(show_info)

        if show_info["status"] != "Ended":
            if last_episode:
                output_lines.append(last_episode)
                output_lines.append(next_episode)
            else:
                output_lines.append(next_episode)
        else:
            output_lines.append(last_episode)

        for output in output_lines:
            self.bot.privmsg(target, output)

    @command(options_frist=True, aliases=["n"])
    def next(self, mask, target, args):
        """Grab TV Shows Next Episode Info

        %%next <tvshow>...
        """
        show_info = self.get_show(args["<tvshow>"], channel=target)
        if not show_info:
            return

        next_episode = self.build_next_episode(show_info)
        self.bot.privmsg(target, "\x0310[ \x0303{} \x0310] :: \x0F {}".format(show_info["name"], next_episode))

    @command(options_frist=True, aliases=["l"])
    def last(self, mask, target, args):
        """Grab TV Shows Last Episode Info

        %%last <tvshow>...
        """
        show_info = self.get_show(args["<tvshow>"], channel=target)
        if not show_info:
            return

        last_episode = self.build_last_episode(show_info)
        if not last_episode:
            last_episode = "\x0310[\x0F \x0307Last Episode:\x0F Unavailable \x0310]\x0F"

        self.bot.privmsg(target, "\x0310[ \x0303{} \x0310] :: \x0F {}".format(show_info["name"], last_episode))

    def build_next_episode(self, show_info):
        try:
            next_episode = self.get_episode_info(show_info["_links"]["nextepisode"]["href"])
            return "\x0310[\x0F \x0307Next Episode:\x0F S{season:02d}E{number:02d} - {name} ( {air_year} {air_month_str} {air_day} @ {air_time}UTC - \x0303{air_countdown}\x0F ) \x0310]\x0F".format(**next_episode)
        except KeyError:
            if show_info["status"] == "Ended":
                return "\x0310[\x0F Show Has Ended/Canceled \x0310]\x0F"
            else:
                return "\x0310[\x0F \x0307Next Episode:\x0F To Be Announced \x0310]\x0F"

    def build_last_episode(self, show_info):
        try:
            last_episode = self.get_episode_info(show_info["_links"]["previousepisode"]["href"])
            return "\x0310[\x0F \x0307Last Episode:\x0F S{season:02d}E{number:02d} - {name} ( {air_year} {air_month_str} {air_day} @ {air_time}UTC - \x0303{air_countdown}\x0F ) \x0310]\x0F".format(**last_episode)
        except KeyError:
            return None

    def get_show(self, show, channel):
        show = " ".join(show)
        show_info = self.call_api("http://api.tvmaze.com/singlesearch/shows?q={}".format(show))
        if not show_info:
            self.bot.privmsg(channel, "Can not find: '{}'".format(show))
            return None
        return show_info

    def call_api(self, url):
        try: 
            return requests.get(url).json()
        except json.decoder.JSONDecodeError:
            return None
        
    def get_episode_info(self, url):
        try:
            episode_info = self.call_api(url)
            return {**episode_info, **self.date_info(episode_info["airstamp"])}
        except KeyError:
            pass

    def date_info(self, air_stamp):
        air_date, air_time = re.match("(.+)T(.+)\+.*", air_stamp).groups()

        air_stamp = datetime.datetime.strptime(
            " ".join([air_date, air_time]).strip(" "),
            "%Y-%m-%d %H:%M:%S"
        )

        air_countdown = []
        current_date_utc = datetime.datetime.utcnow()
        if air_stamp > current_date_utc:
            finished = air_stamp - current_date_utc
            air_countdown.append("from now")
        else:
            finished = current_date_utc - air_stamp
            air_countdown.append("ago")

        mins = int((finished.seconds // 60) % 60)
        hours = int(finished.seconds // (60 * 60))
        days = int(finished.total_seconds() // (60 * 60 * 24))
        if mins:
            air_countdown.insert(0, "{}m".format(mins))
        if hours:
            air_countdown.insert(0, "{}h".format(hours))
        if days:
            air_countdown.insert(0, "{}d".format(days))

        year, month, day = [int(i) for i in air_date.split("-")]

        return {
            "air_year": year,
            "air_month_int": month,
            "air_month_str": datetime.date(year, month, day).strftime("%b"),
            "air_day": day,
            "air_time": air_time,
            "air_countdown": " ".join(air_countdown)
        }
