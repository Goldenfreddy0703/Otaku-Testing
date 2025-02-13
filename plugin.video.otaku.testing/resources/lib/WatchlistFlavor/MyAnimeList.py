import re
import time
import random
import pickle
import json

from resources.lib.ui import utils, client, control, get_meta, database
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase
from resources.lib.ui.divide_flavors import div_flavor
from resources.lib.endpoints import simkl, anilist


class MyAnimeListWLF(WatchlistFlavorBase):
    _NAME = "mal"
    _URL = "https://api.myanimelist.net/v2"
    _TITLE = "MyAnimeList"
    _IMAGE = "myanimelist.png"

    def __headers(self):
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        return headers

    def login(self):
        from urllib import parse
        parsed = parse.urlparse(self.auth_var)
        params = dict(parse.parse_qsl(parsed.query))
        code = params.get('code')
        code_verifier = params.get('state')

        oauth_url = 'https://myanimelist.net/v1/oauth2/token'
        data = {
            'client_id': 'a8d85a4106b259b8c9470011ce2f76bc',
            'code': code,
            'code_verifier': code_verifier,
            'grant_type': 'authorization_code'
        }
        r = client.request(oauth_url, post=data)
        if not r:
            return
        res = json.loads(r)

        self.token = res['access_token']
        user = client.request(f'{self._URL}/users/@me', headers=self.__headers(), params={'fields': 'name'})
        user = json.loads(user)

        login_data = {
            'token': res['access_token'],
            'refresh': res['refresh_token'],
            'expiry': int(time.time()) + int(res['expires_in']),
            'username': user['name']
        }
        return login_data

    @staticmethod
    def refresh_token():
        oauth_url = 'https://myanimelist.net/v1/oauth2/token'
        data = {
            'client_id': 'a8d85a4106b259b8c9470011ce2f76bc',
            'grant_type': 'refresh_token',
            'refresh_token': control.getSetting('mal.refresh')
        }
        r = client.request(oauth_url, post=data, jpost=True)
        if not r:
            return
        res = json.loads(r)
        control.setSetting('mal.token', res['access_token'])
        control.setSetting('mal.refresh', res['refresh_token'])
        control.setInt('mal.expiry', int(time.time()) + int(res['expires_in']))

    @staticmethod
    def handle_paging(hasnextpage, base_url, page):
        if not hasnextpage or not control.is_addon_visible() and control.getBool('widget.hide.nextpage'):
            return []
        next_page = page + 1
        name = "Next Page (%d)" % next_page
        offset = (re.compile("offset=(.+?)&").findall(hasnextpage))[0]
        return [utils.allocate_item(name, f'{base_url}/{offset}?page={next_page}', True, False, [], 'next.png', {'plot': name}, fanart='next.png')]

    def __get_sort(self):
        sort_types = ['list_score', 'list_updated_at', 'anime_start_date', 'anime_title']
        return sort_types[int(self.sort)]

    def watchlist(self):
        statuses = [
            ("Next Up", "watching?next_up=true", 'next_up.png'),
            ("Currently Watching", "watching", 'currently_watching.png'),
            ("Completed", "completed", 'completed.png'),
            ("On Hold", "on_hold", 'on_hold.png'),
            ("Dropped", "dropped", 'dropped.png'),
            ("Plan to Watch", "plan_to_watch", 'want_to_watch.png'),
            ("All Anime", "", 'all_anime.png')
        ]
        return [utils.allocate_item(res[0], f'watchlist_status_type/{self._NAME}/{res[1]}', True, False, [], res[2], {}) for res in statuses]

    @staticmethod
    def action_statuses():
        actions = [
            ("Add to On Currently Watching", "watching"),
            ("Add to Completed", "completed"),
            ("Add to On Hold", "on_hold"),
            ("Add to Dropped", "dropped"),
            ("Add to Plan to Watch", "plan_to_watch"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]
        return actions

    def get_watchlist_status(self, status, next_up, offset, page):
        fields = [
            'alternative_titles',
            'list_status',
            'num_episodes',
            'synopsis',
            'mean',
            'rating',
            'genres',
            'studios',
            'start_date',
            'average_episode_duration',
            'media_type',
            'status'
        ]
        params = {
            "status": status,
            "sort": self.__get_sort(),
            "limit": control.getInt('interface.perpage.watchlist'),
            "offset": offset,
            "fields": ','.join(fields),
            "nsfw": True
        }
        url = f'{self._URL}/users/@me/animelist'
        return self._process_status_view(url, params, next_up, f'watchlist_status_type_pages/mal/{status}', page)

    def _process_status_view(self, url, params, next_up, base_plugin_url, page):
        r = client.request(url, headers=self.__headers(), params=params)
        results = json.loads(r) if r else {}

        # Extract mal_ids and create a list of dictionaries with 'mal_id' keys
        mal_ids = [{'mal_id': item['node']['id']} for item in results.get('data', [])]
        get_meta.collect_meta(mal_ids)

        all_results = list(map(self._base_next_up_view, results['data'])) if next_up else list(map(self._base_watchlist_status_view, results['data']))
        all_results += self.handle_paging(results.get('paging', {}).get('next'), base_plugin_url, page)
        return all_results

    @div_flavor
    def _base_watchlist_status_view(self, res, mal_dub=None):
        mal_id = res['node']['id']

        if not mal_id:
            control.log(f"Mal ID not found for {mal_id}", 'warning')

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        title = res['node'].get('title')
        if self.title_lang == 'english':
            title = res['node']['alternative_titles'].get('en') or title

        eps_watched = res['list_status']["num_episodes_watched"]
        eps = res['node']["num_episodes"]
        image = res['node']['main_picture'].get('large', res['node']['main_picture']['medium'])

        info = {
            'UniqueIDs': {
                'mal_id': str(mal_id),
                **database.get_mapping_ids(mal_id, 'mal_id')
            },
            'title': title,
            'plot': res['node']['synopsis'],
            'rating': {'score': res['node'].get('mean', 0)},
            'duration': res['node']['average_episode_duration'],
            'genre': [x.get('name') for x in res['node']['genres']],
            'status': res['node']['status'],
            'mpaa': res['node'].get('rating'),
            'mediatype': 'tvshow',
            'studio': [x.get('name') for x in res['node']['studios']]
        }

        if start_date := res['node'].get('start_date'):
            info['premiered'] = start_date
            info['year'] = int(start_date[:4])

        if eps_watched == eps and eps != 0:
            info['playcount'] = 1

        show_meta = database.get_show_meta(mal_id)
        kodi_meta = pickle.loads(show_meta.get('art')) if show_meta else {}
        base = {
            "name": f"{title} - {eps_watched}/{eps}",
            "url": f'watchlist_to_ep/{mal_id}/{eps_watched}',
            "image": image,
            "poster": image,
            'fanart': kodi_meta['fanart'] if kodi_meta.get('fanart') else image,
            "info": info
        }

        if kodi_meta.get('thumb'):
            base['landscape'] = random.choice(kodi_meta['thumb'])
        if kodi_meta.get('clearart'):
            base['clearart'] = random.choice(kodi_meta['clearart'])
        if kodi_meta.get('clearlogo'):
            base['clearlogo'] = random.choice(kodi_meta['clearlogo'])

        if res['node']['media_type'] == 'movie' and eps == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)

    @div_flavor
    def _base_next_up_view(self, res, mal_dub=None):
        mal_id = res['node']['id']
        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        eps_watched = res['list_status']["num_episodes_watched"]
        next_up = eps_watched + 1
        eps_total = res['node']["num_episodes"]

        if not control.getBool('playlist.unaired'):
            airing_episode = simkl.Simkl().get_calendar_data(mal_id)
            if not airing_episode:
                airing_episode = anilist.Anilist().get_airing_calendar(mal_id)

            if airing_episode:
                eps_total = airing_episode

        if 0 < eps_total < next_up:
            return

        base_title = res['node']['title']
        if self.title_lang == 'english':
            base_title = res['node']['alternative_titles'].get('en') or base_title

        title = f"{base_title} - {next_up}/{eps_total}"
        poster = image = res['node']['main_picture'].get('large', res['node']['main_picture']['medium'])

        mal_id, next_up_meta, show = self._get_next_up_meta(mal_id, eps_watched)
        if next_up_meta:
            if next_up_meta.get('title'):
                title = f'{title} - {next_up_meta["title"]}'
            if next_up_meta.get('image'):
                image = next_up_meta['image']
            plot = next_up_meta.get('plot')
            aired = next_up_meta.get('aired')
        else:
            plot = aired = None

        info = {
            'UniqueIDs': {
                'mal_id': str(mal_id),
                **database.get_mapping_ids(mal_id, 'mal_id')
            },
            'episode': next_up,
            'title': title,
            'tvshowtitle': base_title,
            'duration': res['node']['average_episode_duration'],
            'plot': plot,
            'mediatype': 'episode',
            'aired': aired
        }

        base = {
            "name": title,
            "url": f'watchlist_to_ep/{mal_id}/{eps_watched}',
            "image": image,
            "info": info,
            "fanart": image,
            "poster": poster
        }

        show_meta = database.get_show_meta(mal_id)
        if show_meta:
            art = pickle.loads(show_meta['art'])
            if art.get('fanart'):
                base['fanart'] = art['fanart']
            if art.get('thumb'):
                base['landscape'] = random.choice(art['thumb'])
            if art.get('clearart'):
                base['clearart'] = random.choice(art['clearart'])
            if art.get('clearlogo'):
                base['clearlogo'] = random.choice(art['clearlogo'])

        if res['node']['media_type'] == 'movie' and eps_total == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)

        if next_up_meta:
            base['url'] = f"play/{mal_id}/{next_up}"
            return utils.parse_view(base, False, True, dub)

        return utils.parse_view(base, True, False, dub)

    def get_watchlist_anime_entry(self, mal_id):
        params = {
            "fields": 'my_list_status'
        }

        url = f'{self._URL}/anime/{mal_id}'
        r = client.request(url, headers=self.__headers(), params=params)
        results = json.loads(r).get('my_list_status') if r else {}
        if not results:
            return {}
        anime_entry = {
            'eps_watched': results['num_episodes_watched'],
            'status': results['status'],
            'score': results['score']
        }
        return anime_entry

    def save_completed(self):
        import json

        data = self.get_user_anime_list('completed')
        completed_ids = {}
        for dat in data:
            mal_id = dat['node']['id']
            try:
                completed_ids[str(mal_id)] = int(dat['node']['num_episodes'])
            except KeyError:
                pass

        with open(control.completed_json, 'w') as file:
            json.dump(completed_ids, file)

    def get_user_anime_list(self, status):
        fields = [
            'list_status',
            'num_episodes',
            'status'
        ]
        params = {
            'status': status,
            "nsfw": True,
            'limit': 1000,
            "fields": ','.join(fields)
        }
        r = client.request(f'{self._URL}/users/@me/animelist', headers=self.__headers(), params=params)
        res = json.loads(r) if r else {}
        paging = res.get('paging', {})
        data = res.get('data', [])
        while paging.get('next'):
            r = client.request(paging['next'], headers=self.__headers())
            res = json.loads(r) if r else {}
            paging = res.get('paging', {})
            data += res.get('data', [])
        return data

    def update_list_status(self, mal_id, status):
        data = {
            "status": status,
        }
        r = client.request(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), post=data, method='PUT')
        return r is not None

    def update_num_episodes(self, mal_id, episode):
        data = {
            'num_watched_episodes': int(episode)
        }
        r = client.request(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), post=data, method='PUT')
        return r is not None

    def update_score(self, mal_id, score):
        data = {
            "score": score,
        }
        r = client.request(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), post=data, method='PUT')
        return r is not None

    def delete_anime(self, mal_id):
        r = client.request(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), method='DELETE')
        return r is not None
