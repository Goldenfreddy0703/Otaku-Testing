import time
import random
import pickle
import json

from resources.lib.ui import client, control, database, utils, get_meta
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase
from resources.lib.indexers.simkl import SIMKLAPI
from resources.lib.endpoints import simkl, anilist
from urllib import parse

from resources.lib.ui.divide_flavors import div_flavor


class KitsuWLF(WatchlistFlavorBase):
    _NAME = "kitsu"
    _URL = "https://kitsu.io/api"
    _TITLE = "Kitsu"
    _IMAGE = "kitsu.png"
    _mapping = None

    def __headers(self):
        headers = {
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json',
            'Authorization': f'Bearer {self.token}'
        }
        return headers

    def login(self):
        params = {
            "grant_type": "password",
            "username": self.auth_var,
            "password": self.password
        }
        resp = client.request(f'{self._URL}/oauth/token', post=params, jpost=True)

        if not resp:
            return

        data = json.loads(resp)
        self.token = data['access_token']
        resp2 = client.request(f'{self._URL}/edge/users', headers=self.__headers(), params={'filter[self]': True})
        data2 = json.loads(resp2)["data"][0]

        login_data = {
            'username': data2["attributes"]["name"],
            'userid': data2['id'],
            'token': data['access_token'],
            'refresh': data['refresh_token'],
            'expiry': int(time.time()) + int(data['expires_in'])
        }
        return login_data

    def refresh_token(self):
        params = {
            "grant_type": "refresh_token",
            "refresh_token": control.getSetting('kitsu.refresh')
        }
        resp = client.request(f'{self._URL}/oauth/token', post=params, jpost=True)

        if not resp:
            return

        data = json.loads(resp)
        control.setSetting('kitsu.token', data['access_token'])
        control.setSetting('kitsu.refresh', data['refresh_token'])
        control.setInt('kitsu.expiry', int(time.time() + int(data['expires_in'])))

    @staticmethod
    def handle_paging(hasnextpage, base_url, page):
        if not hasnextpage or not control.is_addon_visible() and control.getBool('widget.hide.nextpage'):
            return []
        next_page = page + 1
        name = "Next Page (%d)" % next_page
        parsed = parse.urlparse(hasnextpage)
        offset = parse.parse_qs(parsed.query)['page[offset]'][0]
        return [utils.allocate_item(name, f'{base_url}/{offset}?page={next_page}', True, False, [], 'next.png', {'plot': name}, fanart='next.png')]

    def __get_sort(self):
        sort_types = ['-progressed_at', '-progress', f"anime.titles.{self.__get_title_lang()}"]
        return sort_types[int(self.sort)]

    def __get_title_lang(self):
        title_langs = {
            "english": "en",
            "romaji": "en_jp",
        }
        return title_langs[self.title_lang]

    def watchlist(self):
        statuses = [
            ("Next Up", "current?next_up=true", 'next_up.png'),
            ("Current", "current", 'currently_watching.png'),
            ("Want to Watch", "planned", 'want_to_watch.png'),
            ("Completed", "completed", 'completed.png'),
            ("On Hold", "on_hold", 'on_hold.png'),
            ("Dropped", "dropped", 'dropped.png')
        ]
        return [utils.allocate_item(res[0], f'watchlist_status_type/{self._NAME}/{res[1]}', True, False, [], res[2], {}) for res in statuses]

    @staticmethod
    def action_statuses():
        actions = [
            ("Add to Current", "current"),
            ("Add to Want to Watch", "planned"),
            ("Add to On Hold", "on_hold"),
            ("Add to Completed", "completed"),
            ("Add to Dropped", "dropped"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]
        return actions

    def get_watchlist_status(self, status, next_up, offset, page):
        url = f'{self._URL}/edge/library-entries'
        params = {
            "fields[anime]": "titles,canonicalTitle,posterImage,episodeCount,synopsis,episodeLength,subtype,averageRating,ageRating,youtubeVideoId",
            "filter[user_id]": self.user_id,
            "filter[kind]": "anime",
            "filter[status]": status,
            "include": "anime,anime.mappings,anime.mappings.item",
            "page[limit]": control.getSetting('interface.perpage.watchlist'),
            "page[offset]": offset,
            "sort": self.__get_sort(),
        }
        return self.process_watchlist_view(url, params, next_up, f'watchlist_status_type_pages/kitsu/{status}', page)

    def process_watchlist_view(self, url, params, next_up, base_plugin_url, page):
        result = client.request(url, headers=self.__headers(), params=params)
        result = json.loads(result) if result else {}
        _list = result.get("data", [])

        if not result.get('included'):
            result['included'] = []

        el = result["included"][:len(_list)]
        self.mapping = [x for x in result['included'] if x['type'] == 'mappings']

        # Extract mal_ids from the new API response structure
        mal_ids = [{'mal_id': item['attributes']['externalId']} for item in self.mapping if item['attributes']['externalSite'] == 'myanimelist/anime']
        get_meta.collect_meta(mal_ids)

        if next_up:
            all_results = map(self._base_next_up_view, _list, el)
        else:
            all_results = map(self._base_watchlist_view, _list, el)

        all_results = list(all_results)
        all_results += self.handle_paging(result['links'].get('next'), base_plugin_url, page)
        return all_results

    @div_flavor
    def _base_watchlist_view(self, res, eres, mal_dub=None):
        kitsu_id = eres['id']
        mal_id = self.mapping_mal(kitsu_id)

        if not mal_id:
            control.log(f"Mal ID not found for {kitsu_id}", 'warning')

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        info = {
            'UniqueIDs': {
                'kitsu_id': str(kitsu_id),
                'mal_id': str(mal_id),
                **database.get_mapping_ids(kitsu_id, 'kitsu_id'),
                **database.get_mapping_ids(mal_id, 'mal_id')
            },
            'plot': eres['attributes'].get('synopsis'),
            'title': eres["attributes"]["titles"].get(self.__get_title_lang(), eres["attributes"]['canonicalTitle']),
            'mpaa': eres['attributes']['ageRating'],
            'trailer': 'plugin://plugin.video.youtube/play/?video_id={0}'.format(eres['attributes']['youtubeVideoId']),
            'mediatype': 'tvshow'
        }

        if eres['attributes']['episodeCount'] != 0 and res["attributes"]["progress"] == eres['attributes']['episodeCount']:
            info['playcount'] = 1

        try:
            info['duration'] = eres['attributes']['episodeLength'] * 60
        except TypeError:
            pass

        try:
            info['rating'] = {'score': float(eres['attributes']['averageRating']) / 10}
        except TypeError:
            pass

        show_meta = database.get_show_meta(mal_id)
        kodi_meta = pickle.loads(show_meta.get('art')) if show_meta else {}
        poster_image = eres["attributes"]['posterImage']
        base = {
            "name": '%s - %d/%d' % (eres["attributes"]["titles"].get(self.__get_title_lang(), eres["attributes"]['canonicalTitle']),
                                    res["attributes"]['progress'],
                                    eres["attributes"].get('episodeCount', 0) if eres["attributes"]['episodeCount'] else 0),
            "url": f'watchlist_to_ep/{mal_id}/{res["attributes"]["progress"]}',
            "image": poster_image.get('large', poster_image['original']),
            'fanart': kodi_meta['fanart'] if kodi_meta.get('fanart') else poster_image.get('large', poster_image['original']),
            "info": info
        }

        if kodi_meta.get('thumb'):
            base['landscape'] = random.choice(kodi_meta['thumb'])
        if kodi_meta.get('clearart'):
            base['clearart'] = random.choice(kodi_meta['clearart'])
        if kodi_meta.get('clearlogo'):
            base['clearlogo'] = random.choice(kodi_meta['clearlogo'])

        if eres['attributes']['subtype'] == 'movie' and eres['attributes']['episodeCount'] == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)

    @div_flavor
    def _base_next_up_view(self, res, eres, mal_dub=None):
        kitsu_id = eres['id']
        mal_id = self.mapping_mal(kitsu_id)
        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        progress = res["attributes"]['progress']
        next_up = progress + 1
        anime_title = eres["attributes"]["titles"].get(self.__get_title_lang(), eres["attributes"]['canonicalTitle'])
        episode_count = eres["attributes"]['episodeCount'] if eres["attributes"]['episodeCount'] else 0

        if not control.getBool('playlist.unaired'):
            airing_episode = simkl.Simkl().get_calendar_data(mal_id)
            if not airing_episode:
                airing_episode = anilist.Anilist().get_airing_calendar(mal_id)

            if airing_episode:
                episode_count = airing_episode

        title = '%s - %d/%d' % (anime_title, next_up, episode_count)
        poster = image = eres["attributes"]['posterImage'].get('large', eres["attributes"]['posterImage']['original'])
        plot = aired = None

        mal_id, next_up_meta, show = self._get_next_up_meta(mal_id, int(progress))
        if next_up_meta:
            if next_up_meta.get('title'):
                title = '%s - %s' % (title, next_up_meta['title'])
            if next_up_meta.get('image'):
                image = next_up_meta['image']
            plot = next_up_meta.get('plot')
            aired = next_up_meta.get('aired')

        info = {
            'UniqueIDs': {
                'kitsu_id': str(kitsu_id),
                'mal_id': str(mal_id),
                **database.get_mapping_ids(kitsu_id, 'kitsu_id'),
                **database.get_mapping_ids(mal_id, 'mal_id')
            },
            'episode': next_up,
            'title': title,
            'tvshowtitle': anime_title,
            'plot': plot,
            'mediatype': 'episode',
            'aired': aired
        }

        base = {
            "name": title,
            "url": f'watchlist_to_ep/{mal_id}/{res["attributes"]["progress"]}',
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

        if next_up_meta:
            # Ensure mal_id and next_up are integers
            mal_id = int(mal_id)
            next_up = int(next_up)

            # Format the string with integers
            base['url'] = f"play/{mal_id}/{next_up}"
            return utils.parse_view(base, False, True, dub)

        if eres['attributes']['subtype'] == 'movie' and eres['attributes']['episodeCount'] == 1:
            base['url'] = f"play_movie/{mal_id}/"
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)

        return utils.parse_view(base, True, False, dub)

    def mapping_mal(self, kitsu_id):
        mal_id = ''
        for i in self.mapping:
            if i['attributes']['externalSite'] == 'myanimelist/anime':
                if i['relationships']['item']['data']['id'] == kitsu_id:
                    mal_id = i['attributes']['externalId']
                    break
        if not mal_id:
            ids = SIMKLAPI().get_mapping_ids('kitsu', kitsu_id)
            mal_id = ids['mal']
            database.add_mapping_id(mal_id, 'mal_id', mal_id)
        return mal_id

    def get_library_entries(self, kitsu_id):
        params = {
            "filter[user_id]": self.user_id,
            "filter[anime_id]": kitsu_id
        }
        r = client.request(f'{self._URL}/edge/library-entries', headers=self.__headers(), params=params)
        r = json.loads(r) if r else {}
        return r

    def get_watchlist_anime_entry(self, mal_id):
        kitsu_id = self._get_mapping_id(mal_id, 'kitsu_id')
        if not kitsu_id:
            return {}

        result = self.get_library_entries(kitsu_id)
        try:
            item_dict = result['data'][0]['attributes']
        except IndexError:
            return {}
        anime_entry = {
            'eps_watched': item_dict['progress'],
            'status': item_dict['status'],
            'score': item_dict['ratingTwenty']
        }
        return anime_entry

    def save_completed(self):
        import json
        data = self.get_user_anime_list('completed')
        completed = {}
        for dat in data:
            mal_id = self.mapping_mal(dat['relationships']['anime']['data']['id'])
            completed[str(mal_id)] = dat['attributes']['progress']

        with open(control.completed_json, 'w') as file:
            json.dump(completed, file)

    def get_user_anime_list(self, status):
        url = f'{self._URL}/edge/library-entries'
        params = {
            "filter[user_id]": self.user_id,
            "filter[kind]": "anime",
            "filter[status]": status,
            "page[limit]": "500",
            "include": "anime,anime.mappings,anime.mappings.item",
        }
        r = client.request(url, headers=self.__headers(), params=params)
        res = json.loads(r) if r else {}
        paging = res.get('links', {})
        data = res.get('data', [])
        while paging.get('next'):
            r = client.request(paging['next'], headers=self.__headers())
            res = json.loads(r) if r else {}
            paging = res.get('links', {})
            data += res.get('data', [])
        return data

    def update_list_status(self, mal_id, status):
        kitsu_id = self._get_mapping_id(mal_id, 'kitsu_id')
        if not kitsu_id:
            return False

        r = self.get_library_entries(kitsu_id)
        if len(r['data']) == 0:
            data = {
                "data": {
                    "type": "libraryEntries",
                    "attributes": {
                        'status': status
                    },
                    "relationships": {
                        "user": {
                            "data": {
                                "id": self.user_id,
                                "type": "users"
                            }
                        },
                        "anime": {
                            "data": {
                                "id": kitsu_id,
                                "type": "anime"
                            }
                        }
                    }
                }
            }
            r = client.request(f'{self._URL}/edge/library-entries', headers=self.__headers(), post=data, jpost=True)
            return r is not None
        animeid = int(r['data'][0]['id'])
        data = {
            'data': {
                'id': animeid,
                'type': 'libraryEntries',
                'attributes': {
                    'status': status
                }
            }
        }
        r = client.request(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers(), post=data, jpost=True, method='PATCH')
        return r is not None

    def update_num_episodes(self, mal_id, episode):
        kitsu_id = self._get_mapping_id(mal_id, 'kitsu_id')
        if not kitsu_id:
            return False

        r = self.get_library_entries(kitsu_id)
        if len(r['data']) == 0:
            data = {
                "data": {
                    "type": "libraryEntries",
                    "attributes": {
                        'status': 'current',
                        'progress': int(episode)
                    },
                    "relationships": {
                        "user": {
                            "data": {
                                "id": self.user_id,
                                "type": "users"
                            }
                        },
                        "anime": {
                            "data": {
                                "id": kitsu_id,
                                "type": "anime"
                            }
                        }
                    }
                }
            }
            r = client.request(f'{self._URL}/edge/library-entries', headers=self.__headers(), post=data, jpost=True)
            return r is not None

        animeid = int(r['data'][0]['id'])

        data = {
            'data': {
                'id': animeid,
                'type': 'libraryEntries',
                'attributes': {
                    'status': 'current',
                    'progress': int(episode)
                }
            }
        }
        r = client.request(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers(), post=data, jpost=True, method='PATCH')
        return r is not None

    def update_score(self, mal_id, score):
        kitsu_id = self._get_mapping_id(mal_id, 'kitsu_id')
        if not kitsu_id:
            return False

        score = int(score / 10 * 20)
        if score == 0:
            score = None
        r = self.get_library_entries(kitsu_id)
        if len(r['data']) == 0:
            data = {
                "data": {
                    "type": "libraryEntries",
                    "attributes": {
                        'ratingTwenty': score
                    },
                    "relationships": {
                        "user": {
                            "data": {
                                "id": self.user_id,
                                "type": "users"
                            }
                        },
                        "anime": {
                            "data": {
                                "id": kitsu_id,
                                "type": "anime"
                            }
                        }
                    }
                }
            }
            r = client.request(f'{self._URL}/edge/library-entries', headers=self.__headers(), post=data, jpost=True)
            return r is not None

        animeid = int(r['data'][0]['id'])
        data = {
            'data': {
                'id': animeid,
                'type': 'libraryEntries',
                'attributes': {
                    'ratingTwenty': score
                }
            }
        }
        r = client.request(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers(), post=data, jpost=True, method='PATCH')
        return r is not None

    def delete_anime(self, mal_id):
        kitsu_id = self._get_mapping_id(mal_id, 'kitsu_id')
        if not kitsu_id:
            return False

        r = self.get_library_entries(kitsu_id)
        data = r['data']
        if data:
            animeid = data[0]['id']
        else:
            return True

        r = client.request(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers(), method='DELETE')
        return r is not None
