import time
import random
import pickle

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mapping = []

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
        resp = client.post(f'{self._URL}/oauth/token', json_data=params)

        if not resp:
            return

        data = resp.json()
        self.token = data['access_token']
        resp2 = client.get(f'{self._URL}/edge/users', headers=self.__headers(), params={'filter[self]': True})
        data2 = resp2.json()["data"][0]

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
        resp = client.post(f'{self._URL}/oauth/token', json_data=params)

        if not resp:
            return

        data = resp.json()
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
        # Mapping:
        # 0: Anime Title -> sort by anime.titles.{language} alphabetically
        # 1: Score -> sort by anime.averageRating descending
        # 2: Progress -> sort by progress descending
        # 3: Last Updated -> sort by progressed_at descending
        # 4: Last Added -> sort by started_at descending
        sort_options = [
            f"anime.titles.{self.__get_title_lang()}",
            "-anime.averageRating",
            "progress",
            "-progressed_at",
            "-started_at",
        ]
        return sort_options[int(self.sort)]

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
            "page[limit]": control.getInt('interface.perpage.watchlist'),
            "page[offset]": offset,
            "sort": self.__get_sort(),
        }
        return self.process_watchlist_view(url, params, next_up, f'watchlist_status_type_pages/kitsu/{status}', page)

    def process_watchlist_view(self, url, params, next_up, base_plugin_url, page):
        result = client.get(url, headers=self.__headers(), params=params)
        result = result.json() if result else {}
        _list = result.get("data", [])

        if not result.get('included'):
            result['included'] = []

        el = result["included"][:len(_list)]
        self.mapping = [x for x in result['included'] if x['type'] == 'mappings']

        # Extract mal_ids from the new API response structure
        mal_ids = [item['attributes']['externalId'] for item in self.mapping if item['attributes']['externalSite'] == 'myanimelist/anime']
        mal_id_dicts = [{'mal_id': mid} for mid in mal_ids]
        get_meta.collect_meta(mal_id_dicts)

        # Fetch AniList data for all MAL IDs
        try:
            from resources.lib.endpoints.anilist import Anilist
            anilist_data = Anilist().get_anilist_by_mal_ids(mal_ids)
        except Exception:
            anilist_data = []

        # Build AniList lookup by MAL ID (ensure all keys and lookups are strings)
        anilist_by_mal_id = {str(item.get('idMal')): item for item in anilist_data if item.get('idMal')}

        # If order is descending, reverse the order.
        if int(self.order) == 1:
            _list = _list[::-1]
            el = el[::-1]

        # Pass AniList data to view functions
        def viewfunc(res, eres):
            kitsu_id = eres['id']
            mal_id = str(self.mapping_mal(kitsu_id))
            anilist_item = anilist_by_mal_id.get(mal_id)
            return self._base_next_up_view(res, eres, anilist_res=anilist_item) if next_up else self._base_watchlist_view(res, eres, anilist_res=anilist_item)

        all_results = [viewfunc(res, eres) for res, eres in zip(_list, el)]
        all_results += self.handle_paging(result['links'].get('next'), base_plugin_url, page)
        return all_results

    @div_flavor
    def _base_watchlist_view(self, res, eres, mal_dub=None, anilist_res=None):
        kitsu_id = eres['id']
        mal_id = self.mapping_mal(kitsu_id)

        if not mal_id:
            control.log(f"Mal ID not found for {kitsu_id}", level='warning')

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        # Title logic: prefer Kitsu, fallback to AniList
        title = eres["attributes"]["titles"].get(self.__get_title_lang(), eres["attributes"]['canonicalTitle'])
        if anilist_res:
            title = anilist_res.get('title', {}).get(self.title_lang) or anilist_res.get('title', {}).get('romaji') or title
        if title is None:
            title = ''

        # Plot/synopsis
        plot = eres['attributes'].get('synopsis')
        if anilist_res and anilist_res.get('description'):
            desc = anilist_res['description']
            desc = desc.replace('<i>', '[I]').replace('</i>', '[/I]')
            desc = desc.replace('<b>', '[B]').replace('</b>', '[/B]')
            desc = desc.replace('<br>', '[CR]')
            desc = desc.replace('\n', '')
            plot = desc

        # Genres
        genre = None
        if anilist_res:
            genre = anilist_res.get('genres')

        # Studios
        studio = None
        if anilist_res and anilist_res.get('studios'):
            if isinstance(anilist_res['studios'], list):
                studio = [s.get('name') for s in anilist_res['studios']]
            elif isinstance(anilist_res['studios'], dict) and 'edges' in anilist_res['studios']:
                studio = [s['node'].get('name') for s in anilist_res['studios']['edges']]

        # Status
        status = None
        if anilist_res:
            status = anilist_res.get('status')

        # Duration
        duration = None
        if anilist_res and anilist_res.get('duration'):
            duration = anilist_res.get('duration') * 60 if isinstance(anilist_res.get('duration'), int) else anilist_res.get('duration')
        else:
            try:
                duration = eres['attributes']['episodeLength'] * 60
            except TypeError:
                pass

        # Country
        country = None
        if anilist_res:
            country = [anilist_res.get('countryOfOrigin', '')]

        # Rating/score
        info_rating = None
        if anilist_res and anilist_res.get('averageScore'):
            info_rating = {'score': anilist_res.get('averageScore') / 10.0}
            if anilist_res.get('stats') and anilist_res['stats'].get('scoreDistribution'):
                total_votes = sum([score['amount'] for score in anilist_res['stats']['scoreDistribution']])
                info_rating['votes'] = total_votes
        else:
            try:
                info_rating = {'score': float(eres['attributes']['averageRating']) / 10}
            except TypeError:
                pass

        # Trailer
        trailer = None
        if anilist_res and anilist_res.get('trailer'):
            try:
                if anilist_res['trailer']['site'] == 'youtube':
                    trailer = f"plugin://plugin.video.youtube/play/?video_id={anilist_res['trailer']['id']}"
                else:
                    trailer = f"plugin://plugin.video.dailymotion_com/?url={anilist_res['trailer']['id']}&mode=playVideo"
            except (KeyError, TypeError):
                pass
        else:
            trailer = 'plugin://plugin.video.youtube/play/?video_id={0}'.format(eres['attributes']['youtubeVideoId'])

        # Playcount
        playcount = None
        if eres['attributes']['episodeCount'] != 0 and res["attributes"]["progress"] == eres['attributes']['episodeCount']:
            playcount = 1

        # Premiered/year
        premiered = None
        year = None
        if anilist_res and anilist_res.get('startDate'):
            start_date = anilist_res.get('startDate')
            if isinstance(start_date, dict):
                y = start_date.get('year', 0) or 0
                m = start_date.get('month', 1) or 1
                d = start_date.get('day', 1) or 1
                premiered = '{}-{:02}-{:02}'.format(y, m, d)
                year = y if y else None

        # Cast
        cast = None
        if anilist_res and anilist_res.get('characters'):
            try:
                cast = []
                for i, x in enumerate(anilist_res['characters'].get('edges', [])):
                    role = x['node']['name']['userPreferred']
                    actor = x['voiceActors'][0]['name']['userPreferred']
                    actor_hs = x['voiceActors'][0]['image']['large']
                    cast.append({'name': actor, 'role': role, 'thumbnail': actor_hs, 'index': i})
            except (IndexError, KeyError, TypeError):
                pass

        # UniqueIDs
        info_unique_ids = {
            'kitsu_id': str(kitsu_id),
            'mal_id': str(mal_id),
            **database.get_mapping_ids(kitsu_id, 'kitsu_id'),
            **database.get_mapping_ids(mal_id, 'mal_id')
        }

        # Art/Images
        show_meta = database.get_show_meta(mal_id)
        kodi_meta = pickle.loads(show_meta.get('art')) if show_meta else {}
        poster_image = eres["attributes"]['posterImage']
        image = poster_image.get('large', poster_image['original'])
        poster = image
        banner = None
        fanart = kodi_meta.get('fanart', image)
        # AniList fallback for missing images
        if anilist_res and anilist_res.get('coverImage'):
            if not image:
                image = anilist_res['coverImage'].get('extraLarge')
            if not poster:
                poster = anilist_res['coverImage'].get('extraLarge')
            if not fanart:
                fanart = anilist_res['coverImage'].get('extraLarge')
        if anilist_res and anilist_res.get('bannerImage'):
            banner = anilist_res.get('bannerImage')

        info = {
            'UniqueIDs': info_unique_ids,
            'plot': plot,
            'title': title,
            'mpaa': eres['attributes']['ageRating'],
            'trailer': trailer,
            'mediatype': 'tvshow',
            'genre': genre,
            'studio': studio,
            'status': status,
            'duration': duration,
            'country': country,
        }
        if info_rating:
            info['rating'] = info_rating
        if playcount:
            info['playcount'] = playcount
        if premiered:
            info['premiered'] = premiered
        if year:
            info['year'] = year
        if cast:
            info['cast'] = cast

        base = {
            "name": '%s - %d/%d' % (title, res["attributes"]["progress"], eres["attributes"].get('episodeCount', 0) if eres["attributes"]['episodeCount'] else 0),
            "url": f'watchlist_to_ep/{mal_id}/{res["attributes"]["progress"]}',
            "image": image,
            "poster": poster,
            'fanart': fanart,
            "banner": banner,
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
    def _base_next_up_view(self, res, eres, mal_dub=None, anilist_res=None):
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
            ids = SIMKLAPI().get_mapping_ids_from_simkl(kitsu_id, 'kitsu_id')
            mal_id = ids.get('mal', '')
            if mal_id:
                database.add_mapping_id(mal_id, 'mal_id', mal_id)
        return mal_id

    def get_library_entries(self, kitsu_id):
        params = {
            "filter[user_id]": self.user_id,
            "filter[anime_id]": kitsu_id
        }
        r = client.get(f'{self._URL}/edge/library-entries', headers=self.__headers(), params=params)
        r = r.json() if r else {}
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
        r = client.get(url, headers=self.__headers(), params=params)
        res = r.json() if r else {}
        paging = res.get('links', {})
        data = res.get('data', [])
        while paging.get('next'):
            r = client.get(paging['next'], headers=self.__headers())
            res = r.json() if r else {}
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
            r = client.post(f'{self._URL}/edge/library-entries', headers=self.__headers(), json_data=data)
            return r and r.ok
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
        r = client.patch(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers(), json_data=data)
        return r and r.ok

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
            r = client.post(f'{self._URL}/edge/library-entries', headers=self.__headers(), json_data=data)
            return r and r.ok

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
        r = client.patch(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers(), json_data=data)
        return r and r.ok

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
            r = client.post(f'{self._URL}/edge/library-entries', headers=self.__headers(), json_data=data)
            return r and r.ok

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
        r = client.patch(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers(), json_data=data)
        return r and r.ok

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

        r = client.delete(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers())
        return r and r.ok
