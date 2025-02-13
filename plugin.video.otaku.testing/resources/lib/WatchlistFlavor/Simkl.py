import pickle
import random
import json

from resources.lib.ui import utils, database, client, control, get_meta
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase
from resources.lib.ui.divide_flavors import div_flavor
from resources.lib.endpoints import simkl, anilist


class SimklWLF(WatchlistFlavorBase):
    _NAME = 'simkl'
    _URL = 'https://api.simkl.com'
    _TITLE = 'Simkl'
    _NAME = 'simkl'
    _IMAGE = "simkl.png"

    # client_id = '5178a709b7942f1f5077b737b752eea0f6dee684d0e044fa5acee8822a0cbe9b'    # Swag
    # client_id = "503b6b37476926a7a17ac86b95a81b245879955a7531e3e7d8913c0624796ea0"    # JZ
    client_id = "59dfdc579d244e1edf6f89874d521d37a69a95a1abd349910cb056a1872ba2c8"      # Otaku

    def __headers(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f'Bearer {self.token}',
            "simkl-api-key": self.client_id
        }
        return headers

    def login(self):
        params = {
            'client_id': self.client_id,
        }

        r = client.request(f'{self._URL}/oauth/pin', params=params)
        device_code = json.loads(r) if r else {}

        copied = control.copy2clip(device_code["user_code"])
        display_dialog = (f"{control.lang(30020).format(control.colorstr('https://simkl.com/pin'))}[CR]"
                          f"{control.lang(30021).format(control.colorstr(device_code['user_code']))}")
        if copied:
            display_dialog = f"{display_dialog}[CR]{control.lang(30022)}"
        control.progressDialog.create('SIMKL Auth', display_dialog)
        control.progressDialog.update(100)
        inter = int(device_code['expires_in'] / device_code['interval'])
        for i in range(inter):
            if control.progressDialog.iscanceled():
                control.progressDialog.close()
                return
            control.sleep(device_code['interval'] * 1000)

            r = client.request(f'{self._URL}/oauth/pin/{device_code["user_code"]}', params=params)
            r = json.loads(r) if r else {}
            if r.get('result') == 'OK':
                self.token = r['access_token']
                login_data = {'token': self.token}
                r = client.request(f'{self._URL}/users/settings', headers=self.__headers(), post={}, jpost=True)
                if r:
                    user = json.loads(r)['user']
                    login_data['username'] = user['name']
                return login_data
            new_display_dialog = f"{display_dialog}[CR]Code Valid for {control.colorstr(device_code['expires_in'] - i * device_code['interval'])} Seconds"
            control.progressDialog.update(int((inter - i) / inter * 100), new_display_dialog)

    def __get_sort(self):
        sort_types = ['anime_title', 'list_updated_at', 'last_added', 'user_rating']
        return sort_types[int(self.sort)]

    def watchlist(self):
        statuses = [
            ("Next Up", "watching?next_up=true", 'next_up.png'),
            ("Currently Watching", "watching", 'currently_watching.png'),
            ("Completed", "completed", 'completed.png'),
            ("On Hold", "hold", 'on_hold.png'),
            # ("Dropped", "notinteresting", 'on_hold.png'),
            ("Dropped", "dropped", 'dropped.png'),
            ("Plan to Watch", "plantowatch", 'want_to_watch.png'),
            ("All Anime", "ALL", 'all_anime.png')
        ]
        return [utils.allocate_item(res[0], f'watchlist_status_type/{self._NAME}/{res[1]}', True, False, [], res[2], {}) for res in statuses]

    @staticmethod
    def action_statuses():
        actions = [
            ("Add to On Currently Watching", "watching"),
            ("Add to Completed", "completed"),
            ("Add to On Hold", "hold"),
            ("Add to Dropped", "dropped"),
            # ("Add to Dropped", "notinteresting"),
            ("Add to Plan to Watch", "plantowatch"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]
        return actions

    def _base_watchlist_view(self, res):
        url = f'watchlist_status_type/{self._NAME}/{res[1]}'
        return [utils.allocate_item(res[0], url, True, False, [], f'{res[0].lower()}.png', {})]

    def get_watchlist_status(self, status, next_up, offset, page):
        results = self.get_all_items(status)

        if not results:
            return []

        # Extract mal_ids from the new API response structure
        mal_ids = [{'mal_id': anime['show']['ids']['mal']} for anime in results['anime']]
        get_meta.collect_meta(mal_ids)

        all_results = list(map(self._base_next_up_view, results['anime'])) if next_up else list(map(self._base_watchlist_status_view, results['anime']))

        sort_pref = self.__get_sort()

        if sort_pref == '2':  # anime_title
            all_results = sorted(all_results, key=lambda x: x['info']['title'])
        elif sort_pref == '0':    # list_updated_at
            all_results = sorted(all_results, key=lambda x: x['info']['last_watched'] or "0", reverse=True)
        elif sort_pref == '3':    # user_rating
            all_results = sorted(all_results, key=lambda x: x['info']['user_rating'] or 0, reverse=True)
        elif sort_pref == '1':    # last_added
            all_results.reverse()
        return all_results

    @div_flavor
    def _base_watchlist_status_view(self, res, mal_dub=None):
        show_ids = res['show']['ids']
        anilist_id = show_ids.get('anilist')
        mal_id = show_ids.get('mal')
        kitsu_id = show_ids.get('kitsu')

        if not mal_id:
            control.log(f"Mal ID not found for {show_ids}", 'warning')

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show['kodi_meta']) if show else {}

        if self.title_lang == 'english':
            title = kodi_meta.get('ename') or res['show']['title']
        else:
            title = res['show']['title']

        info = {
            'UniqueIDs': {
                'anilist_id': str(anilist_id),
                'mal_id': str(mal_id),
                'kitsu_id': str(kitsu_id),
                **database.get_mapping_ids(anilist_id, 'anilist_id'),
                **database.get_mapping_ids(mal_id, 'mal_id'),
                **database.get_mapping_ids(kitsu_id, 'kitsu_id')
            },
            'title': title,
            'mediatype': 'tvshow',
            'year': res['show']['year'],
            'last_watched': res['last_watched_at'],
            'user_rating': res['user_rating']
        }

        if res["total_episodes_count"] != 0 and res["watched_episodes_count"] == res["total_episodes_count"]:
            info['playcount'] = 1

        image = f'https://wsrv.nl/?url=https://simkl.in/posters/{res["show"]["poster"]}_m.jpg'

        show_meta = database.get_show_meta(mal_id)
        kodi_meta = pickle.loads(show_meta.get('art')) if show_meta else {}
        base = {
            "name": '%s - %d/%d' % (title, res["watched_episodes_count"], res["total_episodes_count"]),
            "url": f'watchlist_to_ep/{mal_id}/{res["watched_episodes_count"]}',
            "image": image,
            'fanart': kodi_meta['fanart'] if kodi_meta.get('fanart') else image,
            "info": info
        }

        if kodi_meta.get('thumb'):
            base['landscape'] = random.choice(kodi_meta['thumb'])
        if kodi_meta.get('clearart'):
            base['clearart'] = random.choice(kodi_meta['clearart'])
        if kodi_meta.get('clearlogo'):
            base['clearlogo'] = random.choice(kodi_meta['clearlogo'])

        if res["total_episodes_count"] == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)

    @div_flavor
    def _base_next_up_view(self, res, mal_dub=None):
        show_ids = res['show']['ids']
        anilist_id = show_ids.get('anilist')
        mal_id = show_ids.get('mal')
        kitsu_id = show_ids.get('kitsu')
        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        progress = res['watched_episodes_count']
        next_up = progress + 1
        episode_count = res["total_episodes_count"]

        if not control.getBool('playlist.unaired'):
            airing_episode = simkl.Simkl().get_calendar_data(mal_id)
            if not airing_episode:
                airing_episode = anilist.Anilist().get_airing_calendar(mal_id)

            if airing_episode:
                episode_count = airing_episode

        if 0 < episode_count < next_up:
            return

        base_title = res['show']['title']

        title = '%s - %s/%s' % (base_title, next_up, episode_count)
        poster = image = f'https://wsrv.nl/?url=https://simkl.in/posters/{res["show"]["poster"]}_m.jpg'
        mal_id, next_up_meta, show = self._get_next_up_meta(mal_id, int(progress))
        if next_up_meta:
            kodi_meta = pickle.loads(show['kodi_meta'])
            if self.title_lang == 'english':
                base_title = kodi_meta.get('ename') or res['show']['title']
                title = '%s - %s/%s' % (base_title, next_up, episode_count)
            if next_up_meta.get('title'):
                title = '%s - %s' % (title, next_up_meta['title'])
            if next_up_meta.get('image'):
                image = next_up_meta['image']
            plot = next_up_meta.get('plot')
            aired = next_up_meta.get('aired')
        else:
            plot = aired = None

        info = {
            'UniqueIDs': {
                'anilist_id': str(anilist_id),
                'mal_id': str(mal_id),
                'kitsu_id': str(kitsu_id),
                **database.get_mapping_ids(anilist_id, 'anilist_id'),
                **database.get_mapping_ids(mal_id, 'mal_id'),
                **database.get_mapping_ids(kitsu_id, 'kitsu_id')
            },
            'episode': next_up,
            'title': title,
            'tvshowtitle': base_title,
            'plot': plot,
            'mediatype': 'episode',
            'aired': aired,
            'last_watched': res['last_watched_at'],
            'user_rating': res['user_rating']
        }

        base = {
            "name": title,
            "url": f'watchlist_to_ep/{mal_id}/{res["watched_episodes_count"]}',
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

        if res["total_episodes_count"] == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)

        if next_up_meta:
            base['url'] = 'play/%d/%d' % (int(mal_id), int(next_up))
            return utils.parse_view(base, False, True, dub)

        return utils.parse_view(base, True, False, dub)

    @staticmethod
    def get_watchlist_anime_entry(mal_id):
        # mal_id = self._get_mapping_id(mal_id, 'mal_id')
        # if not mal_id:
        #     return
        #
        # params = {
        #     'mal': mal_id
        # }
        # r = client.request(f'{self._URL}/sync/watched', headers=self.__headers(), params=params)
        # result = r.json()
        # anime_entry = {
        #     'eps_watched': results['num_episodes_watched'],
        #     'status': results['status'],
        #     'score': results['score']
        # }
        return {}

    def save_completed(self):
        import json
        data = self.get_all_items('completed')
        completed = {}
        for dat in data['anime']:
            completed[str(dat['show']['ids']['mal'])] = dat['total_episodes_count']
        with open(control.completed_json, 'w') as file:
            json.dump(completed, file)

    def get_all_items(self, status):
        # status values: watching, plantowatch, hold ,completed ,dropped (notinteresting for old api's).
        params = {
            'extended': 'full',
            # 'next_watch_info': 'yes'
        }
        r = client.request(f'{self._URL}/sync/all-items/anime/{status}', headers=self.__headers(), params=params)
        return json.loads(r) if r else {}

    def update_list_status(self, mal_id, status):
        data = {
            "shows": [{
                "to": status,
                "ids": {
                    "mal": mal_id
                }
            }]
        }
        r = client.request(f'{self._URL}/sync/add-to-list', headers=self.__headers(), post=data, jpost=True)
        if r:
            r = json.loads(r)
            if not r['not_found']['shows'] or not r['not_found']['shows']:
                if status == 'completed' and r.get('added', {}).get('shows', [{}])[0].get('to') == 'watching':
                    return 'watching'
                return True
        return False

    def update_num_episodes(self, mal_id, episode):
        data = {
            "shows": [{
                "ids": {
                    "mal": mal_id
                },
                "episodes": [{'number': i} for i in range(1, int(episode) + 1)]
            }]
        }
        r = client.request(f'{self._URL}/sync/history', headers=self.__headers(), post=data, jpost=True)
        if r:
            r = json.loads(r)
            if not r['not_found']['shows'] or not r['not_found']['movies']:
                return True
        return False

    def update_score(self, mal_id, score):
        data = {
            "shows": [{
                'rating': score,
                "ids": {
                    "mal": mal_id,
                }
            }]
        }
        url = f"{self._URL}/sync/ratings"
        if score == 0:
            url = f"{url}/remove"

        r = client.request(url, headers=self.__headers(), post=data, jpost=True)
        if r:
            r = json.loads(r)
            if not r['not_found']['shows'] or not r['not_found']['movies']:
                return True
        return False

    def delete_anime(self, mal_id):
        data = {
            "shows": [{
                "ids": {
                    "mal": mal_id
                }
            }]
        }
        r = client.request(f"{self._URL}/sync/history/remove", headers=self.__headers(), post=data, jpost=True)
        if r:
            r = json.loads(r)
            if not r['not_found']['shows'] or not r['not_found']['movies']:
                return True
        return False
