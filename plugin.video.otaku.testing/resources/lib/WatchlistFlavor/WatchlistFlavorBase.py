import pickle
import random
import json

from resources.lib.ui import control, client, database


class WatchlistFlavorBase:
    _URL = None
    _TITLE = None
    _NAME = None
    _IMAGE = None

    def __init__(self, auth_var=None, username=None, password=None, user_id=None, token=None, refresh=None, sort=None):
        self.auth_var = auth_var
        self.username = username
        self.password = password
        self.user_id = user_id
        self.token = token
        self.refresh = refresh
        self.sort = sort
        self.title_lang = ["romaji", 'english'][control.getInt("titlelanguage")]

    @classmethod
    def name(cls):
        return cls._NAME

    @property
    def flavor_name(self):
        return self._NAME

    @property
    def url(self):
        return self._URL

    @property
    def title(self):
        return self._TITLE

    @property
    def image(self):
        return self._IMAGE

    @staticmethod
    def login():
        raise NotImplementedError('Should Not be called Directly')

    @staticmethod
    def get_watchlist_status(status, next_up, offset, page):
        raise NotImplementedError('Should Not be called Directly')

    @staticmethod
    def watchlist():
        raise NotImplementedError('Should Not be called Directly')

    @staticmethod
    def _get_next_up_meta(mal_id, next_up):
        next_up_meta = {}
        show = database.get_show(mal_id)
        if show:
            if show_meta := database.get_show_meta(mal_id):
                art = pickle.loads(show_meta['art'])
                if art.get('fanart'):
                    next_up_meta['image'] = random.choice(art['fanart'])
            if episodes := database.get_episode_list(mal_id):
                try:
                    if episode_meta := pickle.loads(episodes[next_up]['kodi_meta']):
                        if control.getBool('interface.cleantitles'):
                            next_up_meta['title'] = f'Episode {episode_meta["info"]["episode"]}'
                        else:
                            next_up_meta['title'] = episode_meta['info']['title']
                            next_up_meta['plot'] = episode_meta['info']['plot']
                        next_up_meta['image'] = episode_meta['image']['thumb']
                        next_up_meta['aired'] = episode_meta['info'].get('aired')
                except IndexError:
                    pass
        return mal_id, next_up_meta, show

    def _get_mapping_id(self, mal_id, flavor):
        show = database.get_show(mal_id)
        mapping_id = show[flavor] if show and show.get(flavor) else self.get_flavor_id_vercel(mal_id, flavor)
        if not mapping_id:
            mapping_id = self.get_flavor_id_findmyanime(mal_id, flavor)
        return mapping_id

    @staticmethod
    def get_flavor_id_vercel(mal_id, flavor):
        params = {
            'type': "mal",
            "id": mal_id
        }
        response = client.request('https://armkai.vercel.app/api/search', params=params)
        res = json.loads(response) if response else {}
        flavor_id = res.get(flavor[:-3])
        database.add_mapping_id(mal_id, flavor, flavor_id)
        return flavor_id

    @staticmethod
    def get_flavor_id_findmyanime(mal_id, flavor):
        if flavor == 'anilist_id':
            mapping = 'Anilist'
        elif flavor == 'mal_id':
            mapping = 'MyAnimeList'
        elif flavor == 'kitsu_id':
            mapping = 'Kitsu'
        else:
            mapping = None
        params = {
            'id': mal_id,
            'providor': 'MyAnimeList'
        }
        response = client.request('https://find-my-anime.dtimur.de/api', params=params)
        res = json.loads(response) if response else []
        flavor_id = res[0]['providerMapping'][mapping] if res else None
        database.add_mapping_id(mal_id, flavor, flavor_id)
        return flavor_id

    @staticmethod
    def get_flavor_id_simkl(mal_id, flavor):
        from resources.lib.indexers.simkl import SIMKLAPI
        ids = SIMKLAPI().get_mapping_ids(mal_id, flavor)
        flavor_id = ids[flavor]
        database.add_mapping_id(mal_id, flavor, flavor_id)
        return flavor_id
