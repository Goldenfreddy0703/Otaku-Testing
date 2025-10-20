import ast
import json
import pickle
import random
import re
import os

from bs4 import BeautifulSoup
from functools import partial
from resources.lib.ui import database, get_meta, utils, control, client
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.ui.divide_flavors import div_flavor


class AniListBrowser(BrowserBase):
    _BASE_URL = "https://graphql.anilist.co"

    def __init__(self):
        self.title_lang = ["romaji", 'english'][control.getInt("titlelanguage")]
        self.perpage = control.getInt('interface.perpage.general.anilist')
        self.year_type = control.getInt('contentyear.menu') if control.getBool('contentyear.bool') else 0
        self.season_type = control.getInt('contentseason.menu') if control.getBool('contentseason.bool') else -1
        self.format_in_type = ['TV', 'MOVIE', 'TV_SHORT', 'SPECIAL', 'OVA', 'ONA', 'MUSIC'][control.getInt('contentformat.menu')] if control.getBool('contentformat.bool') else ''
        self.status = ['RELEASING', 'FINISHED', 'NOT_YET_RELEASED', 'CANCELLED'][control.getInt('contentstatus.menu.anilist')] if control.getBool('contentstatus.bool') else ''
        self.countryOfOrigin_type = ['JP', 'KR', 'CN', 'TW'][control.getInt('contentorigin.menu')] if control.getBool('contentorigin.bool') else ''
        self.genre = self.load_genres_from_json() if control.getBool('contentgenre.bool') else ''
        self.tag = self.load_tags_from_json() if control.getBool('contentgenre.bool') else ''

        if self.genre == ('',):
            self.genre = ''

        if self.tag == ('',):
            self.tag = ''

    def load_genres_from_json(self):
        if os.path.exists(control.genre_json):
            with open(control.genre_json, 'r') as f:
                settings = json.load(f)
                return tuple(settings.get('selected_genres_anilist', []))
        return ()

    def load_tags_from_json(self):
        if os.path.exists(control.genre_json):
            with open(control.genre_json, 'r') as f:
                settings = json.load(f)
                return tuple(settings.get('selected_tags', []))
        return ()

    def get_season_year(self, period='current'):
        import datetime
        date = datetime.datetime.today()
        year = date.year
        month = date.month
        seasons = ['WINTER', 'SPRING', 'SUMMER', 'FALL']

        if self.year_type:
            if 1916 < self.year_type <= year + 1:
                year = self.year_type
            else:
                control.notify(control.ADDON_NAME, "Invalid year. Please select a year between 1916 and {0}.".format(year + 1))
                return None, None

        if self.season_type > -1:
            season_id = self.season_type
        else:
            season_id = int((month - 1) / 3)

        if period == "next":
            season = seasons[(season_id + 1) % 4]
            if season == 'WINTER':
                year += 1
        elif period == "last":
            season = seasons[(season_id - 1) % 4]
            if season == 'FALL' and month <= 3:
                year -= 1
        else:
            season = seasons[season_id]

        return season, year

    def get_airing_calendar(self, page=1):
        import datetime
        import time
        import itertools

        anilist_cache = self.get_cached_data()
        if anilist_cache:
            list_ = anilist_cache
        else:
            today = datetime.date.today()
            today_ts = int(time.mktime(today.timetuple()))
            weekStart = today_ts - 86400
            weekEnd = today_ts + (86400 * 6)
            variables = {
                'weekStart': weekStart,
                'weekEnd': weekEnd,
                'page': page
            }

            list_ = []

            for i in range(0, 4):
                popular = self.get_airing_calendar_res(variables, page)
                list_.append(popular)

                if not popular['pageInfo']['hasNextPage']:
                    break

                page += 1
                variables['page'] = page

            self.set_cached_data(anilist_cache)

        results = list(map(self.process_airing_view, list_))
        results = list(itertools.chain(*results))
        return results

    def get_cached_data(self):
        if os.path.exists(control.anilist_calendar_json):
            with open(control.anilist_calendar_json, 'r') as f:
                return json.load(f)
        return None

    def set_cached_data(self, data):
        with open(control.anilist_calendar_json, 'w') as f:
            json.dump(data, f)

    def get_airing_last_season(self, page, format, prefix=None):
        season, year = self.get_season_year('last')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "TRENDING_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        airing = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "airing_last_season?page=%d"
        return self.process_anilist_view(airing, base_plugin_url, page)

    def get_airing_this_season(self, page, format, prefix=None):
        season, year = self.get_season_year('this')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        airing = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "airing_this_season?page=%d"
        return self.process_anilist_view(airing, base_plugin_url, page)

    def get_airing_next_season(self, page, format, prefix=None):
        season, year = self.get_season_year('next')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        airing = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "airing_next_season?page=%d"
        return self.process_anilist_view(airing, base_plugin_url, page)

    def get_trending_last_year(self, page, format, prefix=None):
        season, year = self.get_season_year('')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'year': f'{year - 1}%',
            'sort': "TRENDING_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        trending = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "trending_last_year?page=%d"
        return self.process_anilist_view(trending, base_plugin_url, page)

    def get_trending_this_year(self, page, format, prefix=None):
        season, year = self.get_season_year('')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'year': f'{year}%',
            'sort': "TRENDING_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        trending = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "trending_this_year?page=%d"
        return self.process_anilist_view(trending, base_plugin_url, page)

    def get_trending_last_season(self, page, format, prefix=None):
        season, year = self.get_season_year('last')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "TRENDING_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        trending = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "trending_last_season?page=%d"
        return self.process_anilist_view(trending, base_plugin_url, page)

    def get_trending_this_season(self, page, format, prefix=None):
        season, year = self.get_season_year('this')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "TRENDING_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        trending = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "trending_this_season?page=%d"
        return self.process_anilist_view(trending, base_plugin_url, page)

    def get_all_time_trending(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'sort': "TRENDING_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        trending = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "all_time_trending?page=%d"
        return self.process_anilist_view(trending, base_plugin_url, page)

    def get_popular_last_year(self, page, format, prefix=None):
        season, year = self.get_season_year('')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'year': f'{year - 1}%',
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        popular = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "popular_last_year?page=%d"
        return self.process_anilist_view(popular, base_plugin_url, page)

    def get_popular_this_year(self, page, format, prefix=None):
        season, year = self.get_season_year('')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'year': f'{year}%',
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        popular = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "popular_this_year?page=%d"
        return self.process_anilist_view(popular, base_plugin_url, page)

    def get_popular_last_season(self, page, format, prefix=None):
        season, year = self.get_season_year('last')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        popular = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "popular_last_season?page=%d"
        return self.process_anilist_view(popular, base_plugin_url, page)

    def get_popular_this_season(self, page, format, prefix=None):
        season, year = self.get_season_year('this')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        popular = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "popular_this_season?page=%d"
        return self.process_anilist_view(popular, base_plugin_url, page)

    def get_all_time_popular(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        popular = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "all_time_popular?page=%d"
        return self.process_anilist_view(popular, base_plugin_url, page)

    def get_voted_last_year(self, page, format, prefix=None):
        season, year = self.get_season_year('')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'year': f'{year - 1}%',
            'sort': "SCORE_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        voted = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "voted_last_year?page=%d"
        return self.process_anilist_view(voted, base_plugin_url, page)

    def get_voted_this_year(self, page, format, prefix=None):
        season, year = self.get_season_year('')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'year': f'{year}%',
            'sort': "SCORE_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        voted = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "voted_this_year?page=%d"
        return self.process_anilist_view(voted, base_plugin_url, page)

    def get_voted_last_season(self, page, format, prefix=None):
        season, year = self.get_season_year('last')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "SCORE_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        voted = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "voted_last_season?page=%d"
        return self.process_anilist_view(voted, base_plugin_url, page)

    def get_voted_this_season(self, page, format, prefix=None):
        season, year = self.get_season_year('this')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "SCORE_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        voted = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "voted_this_season?page=%d"
        return self.process_anilist_view(voted, base_plugin_url, page)

    def get_all_time_voted(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'sort': "SCORE_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        voted = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "all_time_voted?page=%d"
        return self.process_anilist_view(voted, base_plugin_url, page)

    def get_favourites_last_year(self, page, format, prefix=None):
        season, year = self.get_season_year('')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'year': f'{year - 1}%',
            'sort': "FAVOURITES_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        favourites = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "favourites_last_year?page=%d"
        return self.process_anilist_view(favourites, base_plugin_url, page)

    def get_favourites_this_year(self, page, format, prefix=None):
        season, year = self.get_season_year('')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'year': f'{year}%',
            'sort': "FAVOURITES_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        favourites = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "favourites_this_year?page=%d"
        return self.process_anilist_view(favourites, base_plugin_url, page)

    def get_favourites_last_season(self, page, format, prefix=None):
        season, year = self.get_season_year('last')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "FAVOURITES_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        favourites = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "favourites_last_season?page=%d"
        return self.process_anilist_view(favourites, base_plugin_url, page)

    def get_favourites_this_season(self, page, format, prefix=None):
        season, year = self.get_season_year('this')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "FAVOURITES_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        favourites = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "favourites_this_season?page=%d"
        return self.process_anilist_view(favourites, base_plugin_url, page)

    def get_all_time_favourites(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'sort': "FAVOURITES_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        favourites = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "all_time_favourites?page=%d"
        return self.process_anilist_view(favourites, base_plugin_url, page)

    def get_top_100(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'sort': "SCORE_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if self.genre:
            variables['includedGenres'] = self.genre

        if self.tag:
            variables['includedTags'] = self.tag

        top_100 = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "top_100?page=%d"
        return self.process_anilist_view(top_100, base_plugin_url, page)

    def get_genre_action(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Action",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_action?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_adventure(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Adventure",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_adventure?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_comedy(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Comedy",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_comedy?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_drama(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Drama",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_drama?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_ecchi(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Ecchi",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_ecchi?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_fantasy(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Fantasy",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_fantasy?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_hentai(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Hentai",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_hentai?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_horror(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Horror",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_horror?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_shoujo(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Shoujo",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_shoujo?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_mecha(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Mecha",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_mecha?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_music(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Music",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_music?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_mystery(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Mystery",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_mystery?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_psychological(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Psychological",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_psychological?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_romance(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Romance",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_romance?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_sci_fi(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Sci-Fi",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_sci_fi?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_slice_of_life(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Slice of Life",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_slice_of_life?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_sports(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Sports",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_sports?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_supernatural(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Supernatural",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_supernatural?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_genre_thriller(self, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'includedGenres': "Thriller",
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        genre = database.get(self.get_base_res, 24, variables)
        base_plugin_url = f"{prefix}?page=%d" if prefix else "genre_thriller?page=%d"
        return self.process_anilist_view(genre, base_plugin_url, page)

    def get_search(self, query, page, format, prefix=None):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'search': query,
            'sort': "SEARCH_MATCH",
            'type': "ANIME"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        search = self.get_search_res(variables)
        if control.getBool('search.adult'):
            variables['isAdult'] = True
            search_adult = self.get_search_res(variables)
            for i in search_adult["ANIME"]:
                i['title']['english'] = f'{i["title"]["english"]} - {control.colorstr("Adult", "red")}'
            search['ANIME'] += search_adult['ANIME']
        base_plugin_url = f"{prefix}/{query}?page=%d" if prefix else f"search_anime/{query}?page=%d"
        return self.process_anilist_view(search, base_plugin_url, page)

    def get_recommendations(self, mal_id, page):
        variables = {
            'page': page,
            'perPage': self.perpage,
            'idMal': mal_id
        }
        recommendations = database.get(self.get_recommendations_res, 24, variables)
        return self.process_recommendations_view(recommendations, f'find_recommendations/{mal_id}?page=%d', page)

    def get_relations(self, mal_id):
        variables = {
            'idMal': mal_id
        }
        relations = database.get(self.get_relations_res, 24, variables)
        return self.process_relations_view(relations)

    def get_watch_order(self, mal_id):
        url = 'https://chiaki.site/?/tools/watch_order/id/{}'.format(mal_id)
        response = client.get(url)
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
        else:
            soup = None

        # Find the element with the desired information
        anime_info = soup.find('tr', {'data-id': str(mal_id)})

        watch_order_list = []
        if anime_info is not None:
            # Find all 'a' tags in the entire page with href attributes that match the desired URL pattern
            mal_links = soup.find_all('a', href=re.compile(r'https://myanimelist\.net/anime/\d+'))

            # Extract the MAL IDs from these tags
            mal_ids = [re.search(r'\d+', link['href']).group() for link in mal_links]

            watch_order_list = []
            for idmal in mal_ids:
                variables = {
                    'idMal': int(idmal),
                    'type': "ANIME"
                }

                anilist_item = database.get(self.get_anilist_res_with_mal_id, 24, variables)
                if anilist_item is not None:
                    watch_order_list.append(anilist_item)

        return self.process_watch_order_view(watch_order_list)

    def get_anime(self, mal_id):
        variables = {
            'idMal': mal_id,
            'type': "ANIME"
        }
        anilist_res = database.get(self.get_anilist_res, 24, variables)
        return self.process_res(anilist_res)

    def get_base_res(self, variables):
        query = '''
        query (
            $page: Int=1,
            $perpage: Int=20,
            $type: MediaType,
            $isAdult: Boolean = false,
            $format: [MediaFormat],
            $countryOfOrigin: CountryCode,
            $season: MediaSeason,
            $includedGenres: [String],
            $includedTags: [String],
            $year: String,
            $status: MediaStatus,
            $sort: [MediaSort] = [POPULARITY_DESC, SCORE_DESC]
        ) {
            Page (page: $page, perPage: $perpage) {
                pageInfo {
                    hasNextPage
                }
                ANIME: media (
                    format_in: $format,
                    type: $type,
                    genre_in: $includedGenres,
                    tag_in: $includedTags,
                    season: $season,
                    startDate_like: $year,
                    sort: $sort,
                    status: $status,
                    isAdult: $isAdult,
                    countryOfOrigin: $countryOfOrigin
                ) {
                    id
                    idMal
                    title {
                        romaji,
                        english
                    }
                    coverImage {
                        extraLarge
                    }
                    bannerImage
                    startDate {
                        year,
                        month,
                        day
                    }
                    description
                    synonyms
                    format
                    episodes
                    status
                    genres
                    duration
                    countryOfOrigin
                    averageScore
                    stats {
                        scoreDistribution {
                            score
                            amount
                        }
                    }
                    trailer {
                        id
                        site
                    }
                    characters (
                        page: 1,
                        sort: ROLE,
                        perPage: 10,
                    ) {
                        edges {
                            node {
                                name {
                                    userPreferred
                                }
                            }
                            voiceActors (language: JAPANESE) {
                                name {
                                    userPreferred
                                }
                                image {
                                    large
                                }
                            }
                        }
                    }
                    studios {
                        edges {
                            node {
                                name
                            }
                        }
                    }
                }
            }
        }
        '''

        response = client.post(self._BASE_URL, json_data={'query': query, 'variables': variables})
        results = response.json()

        if "errors" in results.keys():
            return

        json_res = results.get('data', {}).get('Page')

        if control.getBool('general.malposters'):
            try:
                for anime in json_res['ANIME']:
                    anilist_id = anime['id']
                    mal_mapping = database.get_mappings(anilist_id, 'anilist_id')
                    if mal_mapping and 'mal_picture' in mal_mapping:
                        mal_picture = mal_mapping['mal_picture']
                        mal_picture_url = mal_picture.rsplit('.', 1)[0] + 'l.' + mal_picture.rsplit('.', 1)[1]
                        mal_picture_url = 'https://cdn.myanimelist.net/images/anime/' + mal_picture_url
                        anime['coverImage']['extraLarge'] = mal_picture_url
            except Exception:
                pass

        if json_res:
            return json_res

    def get_search_res(self, variables):
        query = '''
        query (
            $page: Int=1,
            $perpage: Int=20
            $type: MediaType,
            $isAdult: Boolean = false,
            $format: [MediaFormat],
            $search: String,
            $sort: [MediaSort] = [SCORE_DESC, POPULARITY_DESC]
        ) {
            Page (page: $page, perPage: $perpage) {
                pageInfo {
                    hasNextPage
                }
                ANIME: media (
                    format_in: $format,
                    type: $type,
                    search: $search,
                    sort: $sort,
                    isAdult: $isAdult
                ) {
                    id
                    idMal
                    title {
                        romaji,
                        english
                    }
                    coverImage {
                        extraLarge
                    }
                    bannerImage
                    startDate {
                        year,
                        month,
                        day
                    }
                    description
                    synonyms
                    format
                    episodes
                    status
                    genres
                    duration
                    countryOfOrigin
                    averageScore
                    stats {
                        scoreDistribution {
                            score
                            amount
                        }
                    }
                    trailer {
                        id
                        site
                    }
                    characters (
                        page: 1,
                        sort: ROLE,
                        perPage: 10,
                    ) {
                        edges {
                            node {
                                name {
                                    userPreferred
                                }
                            }
                            voiceActors (language: JAPANESE) {
                                name {
                                    userPreferred
                                }
                                image {
                                    large
                                }
                            }
                        }
                    }
                    studios {
                        edges {
                            node {
                                name
                            }
                        }
                    }
                }
            }
        }
        '''

        response = client.post(self._BASE_URL, json_data={'query': query, 'variables': variables})
        results = response.json()

        if "errors" in results.keys():
            return

        json_res = results.get('data', {}).get('Page')

        if control.getBool('general.malposters'):
            try:
                for anime in json_res['ANIME']:
                    anilist_id = anime['id']
                    mal_mapping = database.get_mappings(anilist_id, 'anilist_id')
                    if mal_mapping and 'mal_picture' in mal_mapping:
                        mal_picture = mal_mapping['mal_picture']
                        mal_picture_url = mal_picture.rsplit('.', 1)[0] + 'l.' + mal_picture.rsplit('.', 1)[1]
                        mal_picture_url = 'https://cdn.myanimelist.net/images/anime/' + mal_picture_url
                        anime['coverImage']['extraLarge'] = mal_picture_url
            except Exception:
                pass

        if json_res:
            return json_res

    def get_recommendations_res(self, variables):
        query = '''
        query ($idMal: Int, $page: Int, $perpage: Int=20) {
          Media(idMal: $idMal, type: ANIME) {
            id
            recommendations(page: $page, perPage: $perpage, sort: [RATING_DESC, ID]) {
              pageInfo {
                hasNextPage
              }
              edges {
                node {
                  id
                  rating
                  mediaRecommendation {
                    id
                    idMal
                    title {
                      romaji
                      english
                    }
                    genres
                    averageScore
                    description(asHtml: false)
                    coverImage {
                      extraLarge
                    }
                    bannerImage
                    startDate {
                      year
                      month
                      day
                    }
                    format
                    episodes
                    duration
                    status
                    studios {
                      edges {
                        node {
                          name
                        }
                      }
                    }
                    trailer {
                        id
                        site
                    }
                    stats {
                        scoreDistribution {
                            score
                            amount
                        }
                    }
                    characters (perPage: 10) {
                      edges {
                        node {
                          name {
                            full
                            native
                            userPreferred
                          }
                        }
                        voiceActors(language: JAPANESE) {
                          id
                          name {
                            full
                            native
                            userPreferred
                          }
                          image {
                            large
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        '''

        response = client.post(self._BASE_URL, json_data={'query': query, 'variables': variables})
        results = response.json()

        if "errors" in results.keys():
            return

        json_res = results.get('data', {}).get('Media', {}).get('recommendations')

        if control.getBool('general.malposters'):
            try:
                for recommendation in json_res['edges']:
                    anime = recommendation['node']['mediaRecommendation']
                    anilist_id = anime['id']
                    mal_mapping = database.get_mappings(anilist_id, 'anilist_id')
                    if mal_mapping and 'mal_picture' in mal_mapping:
                        mal_picture = mal_mapping['mal_picture']
                        mal_picture_url = mal_picture.rsplit('.', 1)[0] + 'l.' + mal_picture.rsplit('.', 1)[1]
                        mal_picture_url = 'https://cdn.myanimelist.net/images/anime/' + mal_picture_url
                        anime['coverImage']['extraLarge'] = mal_picture_url
            except Exception:
                pass

        if json_res:
            return json_res

    def get_relations_res(self, variables):
        query = '''
        query ($idMal: Int) {
          Media(idMal: $idMal, type: ANIME) {
            relations {
              edges {
                relationType
                node {
                  id
                  idMal
                  title {
                    romaji
                    english
                  }
                  genres
                  averageScore
                  description(asHtml: false)
                  coverImage {
                    extraLarge
                  }
                  bannerImage
                  startDate {
                    year
                    month
                    day
                  }
                  format
                  episodes
                  duration
                  status
                  studios {
                    edges {
                      node {
                        name
                      }
                    }
                  }
                  trailer {
                    id
                    site
                  }
                  stats {
                    scoreDistribution {
                        score
                        amount
                    }
                  }
                  characters (perPage: 10) {
                    edges {
                      node {
                        name {
                          full
                          native
                          userPreferred
                        }
                      }
                      voiceActors(language: JAPANESE) {
                        id
                        name {
                          full
                          native
                          userPreferred
                        }
                        image {
                          large
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        '''

        response = client.post(self._BASE_URL, json_data={'query': query, 'variables': variables})
        results = response.json()

        if "errors" in results.keys():
            return

        json_res = results.get('data', {}).get('Media', {}).get('relations')

        if control.getBool('general.malposters'):
            try:
                for relation in json_res['edges']:
                    anime = relation['node']
                    anilist_id = anime['id']
                    mal_mapping = database.get_mappings(anilist_id, 'anilist_id')
                    if mal_mapping and 'mal_picture' in mal_mapping:
                        mal_picture = mal_mapping['mal_picture']
                        mal_picture_url = mal_picture.rsplit('.', 1)[0] + 'l.' + mal_picture.rsplit('.', 1)[1]
                        mal_picture_url = 'https://cdn.myanimelist.net/images/anime/' + mal_picture_url
                        anime['coverImage']['extraLarge'] = mal_picture_url
            except Exception:
                pass

        if json_res:
            return json_res

    def get_anilist_res(self, variables):
        query = '''
        query($idMal: Int, $type: MediaType){
            Media(idMal: $idMal, type: $type) {
                id
                idMal
                title {
                    romaji,
                    english
                }
                coverImage {
                    extraLarge
                }
                bannerImage
                startDate {
                    year,
                    month,
                    day
                }
                description
                synonyms
                format
                episodes
                status
                genres
                duration
                countryOfOrigin
                averageScore
                characters (
                    page: 1,
                    sort: ROLE,
                    perPage: 10,
                ) {
                    edges {
                        node {
                            name {
                                userPreferred
                            }
                        }
                        voiceActors (language: JAPANESE) {
                            name {
                                userPreferred
                            }
                            image {
                                large
                            }
                        }
                    }
                }
                studios {
                    edges {
                        node {
                            name
                        }
                    }
                }
                trailer {
                    id
                    site
                }
                stats {
                    scoreDistribution {
                        score
                        amount
                    }
                }
            }
        }
        '''

        response = client.post(self._BASE_URL, json_data={'query': query, 'variables': variables})
        results = response.json()

        if "errors" in results.keys():
            return

        json_res = results.get('data', {}).get('Media')

        if json_res:
            return json_res

    def get_airing_calendar_res(self, variables, page=1):
        query = '''
        query (
                $weekStart: Int,
                $weekEnd: Int,
                $page: Int,
        ){
            Page(page: $page) {
                pageInfo {
                        hasNextPage
                        total
                }

                airingSchedules(
                        airingAt_greater: $weekStart
                        airingAt_lesser: $weekEnd
                ) {
                    id
                    episode
                    airingAt
                    media {
                        id
                        idMal
                        title {
                                romaji
                                userPreferred
                                english
                        }
                        description
                        countryOfOrigin
                        genres
                        averageScore
                        isAdult
                        rankings {
                                rank
                                type
                                season
                        }
                        coverImage {
                                extraLarge
                        }
                        bannerImage
                    }
                }
            }
        }
        '''

        response = client.post(self._BASE_URL, json_data={'query': query, 'variables': variables})
        results = response.json()

        if "errors" in results.keys():
            return

        json_res = results.get('data', {}).get('Page')

        if json_res:
            return json_res

    def get_anilist_res_with_mal_id(self, variables):
        query = '''
        query($idMal: Int, $type: MediaType){Media(idMal: $idMal, type: $type) {
            id
            idMal
            title {
                userPreferred,
                romaji,
                english
            }
            coverImage {
                extraLarge
            }
            bannerImage
            startDate {
                year,
                month,
                day
            }
            description
            synonyms
            format
            episodes
            status
            genres
            duration
            countryOfOrigin
            averageScore
            stats {
                scoreDistribution {
                    score
                    amount
                }
            }
            characters (
                page: 1,
                sort: ROLE,
                perPage: 10,
            ) {
                edges {
                    node {
                        name {
                            userPreferred
                        }
                    }
                    voiceActors (language: JAPANESE) {
                        name {
                            userPreferred
                        }
                        image {
                            large
                        }
                    }
                }
            }
            studios {
                edges {
                    node {
                        name
                    }
                }
            }
            }
        }
        '''
        response = client.post(self._BASE_URL, json_data={'query': query, 'variables': variables})
        results = response.json()

        if "errors" in results.keys():
            return

        json_res = results.get('data', {}).get('Media')

        if json_res:
            return json_res

    def process_anilist_view(self, json_res, base_plugin_url, page):
        hasNextPage = json_res['pageInfo']['hasNextPage']
        get_meta.collect_meta(json_res['ANIME'])

        # PERFORMANCE: Seren-style batch fetch of pre-computed metadata
        # Get MAL IDs (prefer API, fallback to mappings database)
        mal_ids = []
        for item in json_res['ANIME']:
            # Try API response first
            mal_id = item.get('idMal')

            # Fallback to mappings database if API doesn't have it
            if not mal_id:
                anilist_id = item.get('id')
                if anilist_id:
                    mappings = database.get_mappings(anilist_id, 'anilist_id')
                    mal_id = mappings.get('mal_id')

            if mal_id:
                mal_ids.append(int(mal_id))
        precomputed_data = database.get_show_list(mal_ids)

        mapfunc = partial(self.base_anilist_view, completed=self.open_completed(), precomputed_data=precomputed_data)
        all_results = list(filter(lambda x: True if x else False, map(mapfunc, json_res['ANIME'])))
        all_results += self.handle_paging(hasNextPage, base_plugin_url, page)
        return all_results

    def process_recommendations_view(self, json_res, base_plugin_url, page):
        hasNextPage = json_res['pageInfo']['hasNextPage']
        res = [edge['node']['mediaRecommendation'] for edge in json_res['edges'] if edge['node']['mediaRecommendation']]
        get_meta.collect_meta(res)

        # PERFORMANCE: Get MAL IDs (prefer API, fallback to mappings database)
        mal_ids = []
        for item in res:
            # Try API response first
            mal_id = item.get('idMal')

            # Fallback to mappings database if API doesn't have it
            if not mal_id:
                anilist_id = item.get('id')
                if anilist_id:
                    mappings = database.get_mappings(anilist_id, 'anilist_id')
                    mal_id = mappings.get('mal_id')

            if mal_id:
                mal_ids.append(int(mal_id))
        precomputed_data = database.get_show_list(mal_ids)

        mapfunc = partial(self.base_anilist_view, completed=self.open_completed(), precomputed_data=precomputed_data)
        all_results = list(filter(lambda x: True if x else False, map(mapfunc, res)))
        all_results += self.handle_paging(hasNextPage, base_plugin_url, page)
        return all_results

    def process_relations_view(self, json_res):
        res = []
        for edge in json_res['edges']:
            if edge['relationType'] != 'ADAPTATION':
                tnode = edge['node']
                tnode['relationType'] = edge['relationType']
                res.append(tnode)
        get_meta.collect_meta(res)

        # PERFORMANCE: Get MAL IDs (prefer API, fallback to mappings database)
        mal_ids = []
        for item in res:
            # Try API response first
            mal_id = item.get('idMal')

            # Fallback to mappings database if API doesn't have it
            if not mal_id:
                anilist_id = item.get('id')
                if anilist_id:
                    mappings = database.get_mappings(anilist_id, 'anilist_id')
                    mal_id = mappings.get('mal_id')

            if mal_id:
                mal_ids.append(int(mal_id))
        precomputed_data = database.get_show_list(mal_ids)

        mapfunc = partial(self.base_anilist_view, completed=self.open_completed(), precomputed_data=precomputed_data)
        all_results = list(filter(lambda x: True if x else False, map(mapfunc, res)))
        return all_results

    def process_watch_order_view(self, json_res):
        res = json_res
        get_meta.collect_meta(res)

        # PERFORMANCE: Get MAL IDs (prefer API, fallback to mappings database)
        mal_ids = []
        for item in res:
            # Try API response first
            mal_id = item.get('idMal')

            # Fallback to mappings database if API doesn't have it
            if not mal_id:
                anilist_id = item.get('id')
                if anilist_id:
                    mappings = database.get_mappings(anilist_id, 'anilist_id')
                    mal_id = mappings.get('mal_id')

            if mal_id:
                mal_ids.append(int(mal_id))
        precomputed_data = database.get_show_list(mal_ids)

        mapfunc = partial(self.base_anilist_view, completed=self.open_completed(), precomputed_data=precomputed_data)
        all_results = list(filter(lambda x: True if x else False, map(mapfunc, res)))
        return all_results

    def process_airing_view(self, json_res):
        import time
        filter_json = [x for x in json_res['airingSchedules'] if x['media']['isAdult'] is False]
        ts = int(time.time())
        mapfunc = partial(self.base_airing_view, ts=ts)
        all_results = list(map(mapfunc, filter_json))
        return all_results

    def process_res(self, res):
        self.database_update_show(res)
        get_meta.collect_meta([res])
        return database.get_show(res['idMal'])

    @div_flavor
    def base_anilist_view(self, res, completed=None, mal_dub=None, precomputed_data=None):
        """
        PERFORMANCE: Seren-style pre-computed metadata approach.

        Uses pre-computed info/cast/art from database instead of building on-the-fly.
        Falls back to on-the-fly building only if pre-computed data is missing.
        """
        if not completed:
            completed = {}

        anilist_id = res['id']
        mal_id = res.get('idMal')

        # Fallback to mappings database if API doesn't have it
        if not mal_id:
            mappings = database.get_mappings(anilist_id, 'anilist_id')
            mal_id = mappings.get('mal_id')

        if not mal_id:
            return

        # PERFORMANCE: Try to use pre-computed data first (Seren pattern)
        use_precomputed = False
        info = None
        cast = None
        art_dict = {}

        if precomputed_data and mal_id in precomputed_data:
            precomp = precomputed_data[mal_id]
            # Check if we have valid pre-computed data
            if precomp.get('info'):
                use_precomputed = True
                info = precomp['info'].copy()  # Get pre-computed info dict
                cast = precomp.get('cast')  # Get pre-computed cast
                art_dict = precomp.get('art', {}).copy()  # Get pre-computed art

        # Fallback: Build metadata on-the-fly if pre-computed data is missing
        if not use_precomputed:
            # Create show in database if it doesn't exist
            if not database.get_show(mal_id):
                self.database_update_show(res)

            # Fetch the newly created pre-computed data
            show_list = database.get_show_list([mal_id])
            if show_list and mal_id in show_list:
                precomp = show_list[mal_id]
                info = precomp.get('info', {}).copy() if precomp.get('info') else {}
                cast = precomp.get('cast')
                art_dict = precomp.get('art', {}).copy() if precomp.get('art') else {}
                use_precomputed = True

        # If still no data, build metadata from res as last resort
        if not info:
            info = {'mediatype': 'tvshow'}

        # Fallback: Build missing metadata fields from res if not in pre-computed data
        if not info.get('plot'):
            if desc := res.get('description'):
                desc = desc.replace('<i>', '[I]').replace('</i>', '[/I]')
                desc = desc.replace('<b>', '[B]').replace('</b>', '[/B]')
                desc = desc.replace('<br>', '[CR]')
                desc = desc.replace('\n', '')
                info['plot'] = desc

        if not info.get('genre'):
            info['genre'] = res.get('genres')

        if not info.get('studio'):
            info['studio'] = [x['node'].get('name') for x in res['studios']['edges']]

        if not info.get('status'):
            info['status'] = res.get('status')

        if not info.get('country'):
            info['country'] = [res.get('countryOfOrigin', '')]

        if not info.get('premiered'):
            try:
                start_date = res.get('startDate')
                info['premiered'] = '{}-{:02}-{:02}'.format(start_date['year'], start_date['month'], start_date['day'])
                if not info.get('year'):
                    info['year'] = start_date['year']
            except (KeyError, TypeError):
                pass

        if not info.get('duration'):
            try:
                info['duration'] = res['duration'] * 60
            except (KeyError, TypeError):
                pass

        if not info.get('rating'):
            try:
                info['rating'] = {'score': res.get('averageScore') / 10.0}
                if res.get('stats') and res['stats'].get('scoreDistribution'):
                    total_votes = sum([score['amount'] for score in res['stats']['scoreDistribution']])
                    info['rating']['votes'] = total_votes
            except (KeyError, TypeError):
                pass

        if not info.get('trailer'):
            try:
                if res['trailer']['site'] == 'youtube':
                    info['trailer'] = f"plugin://plugin.video.youtube/play/?video_id={res['trailer']['id']}"
                else:
                    info['trailer'] = f"plugin://plugin.video.dailymotion_com/?url={res['trailer']['id']}&mode=playVideo"
            except (KeyError, TypeError):
                pass

        if not cast and res.get('characters'):
            try:
                cast = []
                for i, x in enumerate(res['characters']['edges']):
                    role = x['node']['name']['userPreferred']
                    actor = x['voiceActors'][0]['name']['userPreferred']
                    actor_hs = x['voiceActors'][0]['image']['large']
                    cast.append({'name': actor, 'role': role, 'thumbnail': actor_hs, 'index': i})
            except (IndexError, KeyError, TypeError):
                pass

        if not info.get('UniqueIDs'):
            mappings_anilist = database.get_unique_ids(anilist_id, 'anilist_id')
            mappings_mal = database.get_mappings(mal_id, 'mal_id')
            info['UniqueIDs'] = {
                'anilist_id': str(anilist_id),
                'mal_id': str(mal_id),
                **mappings_anilist,
                **mappings_mal
            }

        # PERFORMANCE: No more pickle.loads() - all artwork is in pre-computed art_dict!

        # PERFORMANCE: Use pre-computed title, but allow override for relations
        title = info.get('title', res['title'][self.title_lang] or res['title']['romaji'])

        # Add relation info to title
        if res.get('relationType'):
            title += ' [I]%s[/I]' % control.colorstr(res['relationType'], 'limegreen')

        # Update info dict with the final title
        info['title'] = title

        # PERFORMANCE: Only supplement with dynamic data that changes per-request
        # Most metadata is already in the pre-computed info dict!

        # Add playcount if show is completed (dynamic per-user data)
        if completed.get(str(mal_id)):
            info['playcount'] = 1

        # Add cast if available from pre-computed data
        if cast:
            info['cast'] = cast

        # Dub status (dynamic per-user data)
        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        # PERFORMANCE: Use pre-computed artwork from art_dict
        # Supplement with AniList images for items without pre-computed art
        image = art_dict.get('icon') or art_dict.get('poster')
        poster = art_dict.get('poster')
        fanart = art_dict.get('fanart')
        banner = art_dict.get('banner')

        # Fallback to AniList images if pre-computed art is missing
        anilist_image = res['coverImage']['extraLarge']
        if not image:
            image = anilist_image
        if not poster:
            poster = anilist_image
        if not fanart:
            # Use AniList image as fanart fallback
            fanart = anilist_image
        if not banner:
            banner = res.get('bannerImage')

        base = {
            "name": title,
            "url": f'animes/{mal_id}/',
            "image": image,
            "poster": poster,
            'fanart': fanart,
            "banner": banner,
            "info": info
        }

        # Add extra Fanart.tv artwork from pre-computed art_dict
        if art_dict.get('landscape') or art_dict.get('thumb'):
            base['landscape'] = art_dict.get('landscape') or art_dict.get('thumb')
        if art_dict.get('clearart'):
            base['clearart'] = art_dict.get('clearart')
        if art_dict.get('clearlogo'):
            base['clearlogo'] = art_dict.get('clearlogo')

        # Movie/episode logic
        if res['episodes'] == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)

    def base_airing_view(self, res, ts):
        import datetime

        mal_id = res['media']['idMal']
        if not mal_id:
            return

        airingAt = datetime.datetime.fromtimestamp(res['airingAt'])
        airingAt_day = airingAt.strftime('%A')
        airingAt_time = airingAt.strftime('%I:%M %p')
        airing_status = 'airing' if res['airingAt'] > ts else 'aired'
        rank = None
        rankings = res['media']['rankings']
        if rankings and rankings[-1]['season']:
            rank = rankings[-1]['rank']
        genres = res['media']['genres']
        if genres:
            genres = ' | '.join(genres[:3])
        else:
            genres = 'Genres Not Found'
        title = res['media']['title'][self.title_lang]
        if not title:
            title = res['media']['title']['userPreferred']

        base = {
            'release_title': title,
            'poster': res['media']['coverImage']['extraLarge'],
            'ep_title': '{} {} {}'.format(res['episode'], airing_status, airingAt_day),
            'ep_airingAt': airingAt_time,
            'averageScore': res['media']['averageScore'],
            'rank': rank,
            'plot': res['media']['description'].replace('<br><br>', '[CR]').replace('<br>', '').replace('<i>', '[I]').replace('</i>', '[/I]') if res['media']['description'] else res['media']['description'],
            'genres': genres,
            'id': res['media']['idMal']
        }

        return base

    def database_update_show(self, res):
        mal_id = res.get('idMal')

        if not mal_id:
            return

        try:
            start_date = res['startDate']
            start_date = '{}-{:02}-{:02}'.format(start_date['year'], start_date['month'], start_date['day'])
        except TypeError:
            start_date = None

        try:
            duration = res['duration'] * 60
        except (KeyError, TypeError):
            duration = 0

        title_userPreferred = res['title'][self.title_lang] or res['title']['romaji']

        name = res['title']['romaji']
        ename = res['title']['english']
        titles = f"({name})|({ename})"

        if desc := res.get('description'):
            desc = desc.replace('<i>', '[I]').replace('</i>', '[/I]')
            desc = desc.replace('<b>', '[B]').replace('</b>', '[/B]')
            desc = desc.replace('<br>', '[CR]')
            desc = desc.replace('\n', '')

        kodi_meta = {
            'name': name,
            'ename': ename,
            'title_userPreferred': title_userPreferred,
            'start_date': start_date,
            'query': titles,
            'episodes': res['episodes'],
            'poster': res['coverImage']['extraLarge'],
            'status': res.get('status'),
            'format': res.get('format', ''),
            'plot': desc,
            'duration': duration,
            'genre': res.get('genres'),
            'country': [res.get('countryOfOrigin', '')],
        }

        try:
            start_date = res.get('startDate')
            kodi_meta['premiered'] = '{}-{:02}-{:02}'.format(start_date['year'], start_date['month'], start_date['day'])
            kodi_meta['year'] = start_date['year']
        except TypeError:
            pass

        try:
            cast = []
            for i, x in enumerate(res['characters']['edges']):
                role = x['node']['name']['userPreferred']
                actor = x['voiceActors'][0]['name']['userPreferred']
                actor_hs = x['voiceActors'][0]['image']['large']
                cast.append({'name': actor, 'role': role, 'thumbnail': actor_hs, 'index': i})
            kodi_meta['cast'] = cast
        except IndexError:
            pass

        kodi_meta['studio'] = [x['node'].get('name') for x in res['studios']['edges']]

        try:
            kodi_meta['rating'] = {'score': res.get('averageScore') / 10.0}
            if res.get('stats') and res['stats'].get('scoreDistribution'):
                total_votes = sum([score['amount'] for score in res['stats']['scoreDistribution']])
                kodi_meta['rating']['votes'] = total_votes
        except TypeError:
            pass

        try:
            if res['trailer']['site'] == 'youtube':
                kodi_meta['trailer'] = f"plugin://plugin.video.youtube/play/?video_id={res['trailer']['id']}"
            else:
                kodi_meta['trailer'] = f"plugin://plugin.video.dailymotion_com/?url={res['trailer']['id']}&mode=playVideo"
        except (KeyError, TypeError):
            pass

        # Update legacy kodi_meta (pickle) for backward compatibility
        database.update_show(mal_id, pickle.dumps(kodi_meta))

        # PERFORMANCE: Pre-compute and store metadata as JSON for Seren-style list building
        # Build the info dict that would be passed to InfoTagVideo
        anilist_id = res.get('id')
        mappings_mal = database.get_mappings(mal_id, 'mal_id')
        unique_ids = {'mal_id': str(mal_id)}
        if anilist_id:
            unique_ids['anilist_id'] = str(anilist_id)
            unique_ids.update(database.get_unique_ids(anilist_id, 'anilist_id'))
        unique_ids.update(mappings_mal)

        info_dict = {
            'UniqueIDs': unique_ids,
            'title': title_userPreferred,
            'plot': desc,
            'duration': duration,
            'genre': res.get('genres'),
            'studio': kodi_meta.get('studio'),
            'status': res.get('status'),
            'mediatype': 'tvshow',
            'country': [res.get('countryOfOrigin', '')],
        }
        if kodi_meta.get('rating'):
            info_dict['rating'] = kodi_meta['rating']
        if kodi_meta.get('premiered'):
            info_dict['premiered'] = kodi_meta['premiered']
        if kodi_meta.get('year'):
            info_dict['year'] = kodi_meta['year']
        if kodi_meta.get('trailer'):
            info_dict['trailer'] = kodi_meta['trailer']

        # Build cast list
        cast_list = kodi_meta.get('cast')

        # Build art dict - check shows_meta for Fanart.tv artwork first!
        art_dict = {}
        show_meta = database.get_show_meta(mal_id)
        if show_meta and show_meta.get('art'):
            import pickle as pickle_module
            try:
                # Get fanart/banner/clearlogo/clearart from shows_meta (populated by get_meta)
                meta_art = pickle_module.loads(show_meta['art'])
                if meta_art:
                    # IMPORTANT: Convert list values to single URL strings (Kodi expects strings, not lists)
                    for key, value in meta_art.items():
                        if isinstance(value, list) and len(value) > 0:
                            art_dict[key] = value[0]  # Use first URL from list
                        elif isinstance(value, str):
                            art_dict[key] = value
            except Exception:
                pass

        # Add poster if not already in art_dict
        poster = res['coverImage'].get('extraLarge')
        if poster and not art_dict.get('poster'):
            art_dict['poster'] = poster
        if poster and not art_dict.get('icon'):
            art_dict['icon'] = poster

        # Determine anime_schedule_route
        anime_schedule_route = f'animes/{mal_id}/'

        # Store pre-computed metadata
        database.update_show_precomputed(mal_id, pickle.dumps(kodi_meta), info_dict, cast_list, art_dict, anime_schedule_route)

    def get_genres(self, page, format):
        query = '''
        query {
            genres: GenreCollection,
            tags: MediaTagCollection {
                name
                isAdult
            }
        }
        '''

        response = client.post(self._BASE_URL, json_data={'query': query})
        results = response.json()
        if not results:
            # genres_list = ['Action', 'Adventure', 'Comedy', 'Drama', 'Ecchi', 'Fantasy', 'Hentai', "Horror", 'Mahou Shoujo', 'Mecha', 'Music', 'Mystery', 'Psychological', 'Romance', 'Sci-Fi', 'Slice of Life', 'Sports', 'Supernatural', 'Thriller']
            genres_list = ['error']
        else:
            genres_list = results['data']['genres']
        # if 'Hentai' in genres_list:
        #     genres_list.remove('Hentai')
        try:
            tags_list = [x['name'] for x in results['data']['tags'] if not x['isAdult']]
        except KeyError:
            tags_list = []
        multiselect = control.multiselect_dialog(control.lang(30940), genres_list + tags_list, preselect=[])
        if not multiselect:
            return []
        genre_display_list = []
        tag_display_list = []
        for selection in multiselect:
            if selection < len(genres_list):
                genre_display_list.append(genres_list[selection])
            else:
                tag_display_list.append(tags_list[selection - len(genres_list)])
        return self.genres_payload(genre_display_list, tag_display_list, page, format)

    def genres_payload(self, genre_list, tag_list, page, format, prefix=None):
        query = '''
        query (
            $page: Int=1,
            $perpage: Int=20,
            $type: MediaType,
            $isAdult: Boolean = false,
            $format: [MediaFormat],
            $countryOfOrigin: CountryCode,
            $season: MediaSeason,
            $status: MediaStatus,
            $genre_in: [String],
            $tag_in: [String],
            $sort: [MediaSort] = [POPULARITY_DESC]
        ) {
            Page (page: $page, perPage: $perpage) {
                pageInfo {
                    hasNextPage
                }
                ANIME: media (
                    format_in: $format,
                    type: $type,
                    genre_in: $genre_in,
                    tag_in: $tag_in,
                    season: $season,
                    status: $status,
                    isAdult: $isAdult,
                    countryOfOrigin: $countryOfOrigin,
                    sort: $sort
                ) {
                    id
                    idMal
                    title {
                        romaji,
                        english
                    }
                    coverImage {
                        extraLarge
                    }
                    bannerImage
                    startDate {
                        year,
                        month,
                        day
                    }
                    description
                    synonyms
                    format
                    episodes
                    status
                    genres
                    duration
                    isAdult
                    countryOfOrigin
                    averageScore
                    stats {
                        scoreDistribution {
                            score
                            amount
                        }
                    }
                    trailer {
                        id
                        site
                    }
                    characters (
                        page: 1,
                        sort: ROLE,
                        perPage: 10,
                    ) {
                        edges {
                            node {
                                name {
                                    userPreferred
                                }
                            }
                            voiceActors (language: JAPANESE) {
                                name {
                                    userPreferred
                                }
                                image {
                                    large
                                }
                            }
                        }
                    }
                    studios {
                        edges {
                            node {
                                name
                            }
                        }
                    }
                }
            }
        }
        '''

        if not isinstance(genre_list, list):
            genre_list = ast.literal_eval(genre_list)
        if not isinstance(tag_list, list):
            tag_list = ast.literal_eval(tag_list)

        variables = {
            'page': page,
            'perPage': self.perpage,
            'type': "ANIME",
            'genre_in': genre_list if genre_list else None,
            'tag_in': tag_list if tag_list else None,
            'isAdult': 'Hentai' in genre_list,
            'sort': "POPULARITY_DESC"
        }

        if format:
            variables['format'] = format

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        if self.status:
            variables['status'] = self.status

        if format:
            variables['format'] = format

        try:
            from resources.lib import Main
            prefix = Main.plugin_url.split('/', 1)[0]
            base_plugin_url = f"{prefix}/{genre_list}/{tag_list}?page=%d"
        except Exception:
            base_plugin_url = f"genres/{genre_list}/{tag_list}?page=%d"

        return self.process_genre_view(query, variables, base_plugin_url, page)

    def process_genre_view(self, query, variables, base_plugin_url, page):
        response = client.post(self._BASE_URL, json_data={'query': query, 'variables': variables})
        results = response.json()
        anime_res = results['data']['Page']['ANIME']
        hasNextPage = results['data']['Page']['pageInfo']['hasNextPage']

        genre_filter = variables.get('genre_in')
        if genre_filter and isinstance(genre_filter, (list, tuple)) and len(genre_filter) > 1:
            genre_set = set(genre_filter)
            anime_res = [a for a in anime_res if genre_set.issubset(set(a.get('genres', [])))]

        if control.getBool('general.malposters'):
            try:
                for anime in anime_res:
                    anilist_id = anime['id']
                    mal_mapping = database.get_mappings(anilist_id, 'anilist_id')
                    if mal_mapping and 'mal_picture' in mal_mapping:
                        mal_picture = mal_mapping['mal_picture']
                        mal_picture_url = mal_picture.rsplit('.', 1)[0] + 'l.' + mal_picture.rsplit('.', 1)[1]
                        mal_picture_url = 'https://cdn.myanimelist.net/images/anime/' + mal_picture_url
                        anime['coverImage']['extraLarge'] = mal_picture_url
            except Exception:
                pass

        get_meta.collect_meta(anime_res)

        # PERFORMANCE: Get MAL IDs (prefer API, fallback to mappings database)
        mal_ids = []
        for item in anime_res:
            # Try API response first
            mal_id = item.get('idMal')

            # Fallback to mappings database if API doesn't have it
            if not mal_id:
                anilist_id = item.get('id')
                if anilist_id:
                    mappings = database.get_mappings(anilist_id, 'anilist_id')
                    mal_id = mappings.get('mal_id')

            if mal_id:
                mal_ids.append(int(mal_id))
        precomputed_data = database.get_show_list(mal_ids)

        mapfunc = partial(self.base_anilist_view, completed=self.open_completed(), precomputed_data=precomputed_data)
        all_results = list(map(mapfunc, anime_res))
        all_results += self.handle_paging(hasNextPage, base_plugin_url, page)
        return all_results

    def update_genre_settings(self):
        query = '''
        query {
            genres: GenreCollection,
            tags: MediaTagCollection {
                name
                isAdult
            }
        }
        '''

        response = client.post(self._BASE_URL, json_data={'query': query})
        results = response.json()
        if not results:
            genres_list = ['Action', 'Adventure', 'Comedy', 'Drama', 'Ecchi', 'Fantasy', 'Hentai', "Horror", 'Mahou Shoujo', 'Mecha', 'Music', 'Mystery', 'Psychological', 'Romance', 'Sci-Fi', 'Slice of Life', 'Sports', 'Supernatural', 'Thriller']
        else:
            genres_list = results['data']['genres']

        try:
            tags_list = [x['name'] for x in results['data']['tags'] if not x['isAdult']]
        except KeyError:
            tags_list = []

        multiselect = control.multiselect_dialog(control.lang(30940), genres_list + tags_list, preselect=[])
        if not multiselect:
            return [], []

        selected_genres_anilist = []
        selected_tags = []
        selected_genres_mal = []

        for selection in multiselect:
            if selection < len(genres_list):
                selected_genre = genres_list[selection]
                selected_genres_anilist.append(selected_genre)
            else:
                selected_tag = tags_list[selection - len(genres_list)]
                selected_tags.append(selected_tag)

        return selected_genres_mal, selected_genres_anilist, selected_tags
