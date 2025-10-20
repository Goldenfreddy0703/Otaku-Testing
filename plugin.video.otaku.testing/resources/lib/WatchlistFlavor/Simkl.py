import pickle
import random

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

    api_info = database.get_info('Simkl')
    client_id = api_info['client_id']

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

        r = client.get(f'{self._URL}/oauth/pin', params=params)
        device_code = r.json() if r else {}

        copied = control.copy2clip(device_code["user_code"])
        display_dialog = (f"{control.lang(30021).format(control.colorstr('https://simkl.com/pin'))}[CR]"
                          f"{control.lang(30022).format(control.colorstr(device_code['user_code']))}")
        if copied:
            display_dialog = f"{display_dialog}[CR]{control.lang(30023)}"
        control.progressDialog.create('SIMKL Auth', display_dialog)
        control.progressDialog.update(100)
        inter = int(device_code['expires_in'] / device_code['interval'])
        for i in range(inter):
            if control.progressDialog.iscanceled():
                control.progressDialog.close()
                return
            control.sleep(device_code['interval'] * 1000)

            r = client.get(f'{self._URL}/oauth/pin/{device_code["user_code"]}', params=params)
            r = r.json() if r else {}
            if r.get('result') == 'OK':
                self.token = r['access_token']
                login_data = {'token': self.token}
                r = client.post(f'{self._URL}/users/settings', headers=self.__headers(), json_data={})
                if r:
                    user = r.json()['user']
                    login_data['username'] = user['name']
                return login_data
            new_display_dialog = f"{display_dialog}[CR]Code Valid for {control.colorstr(device_code['expires_in'] - i * device_code['interval'])} Seconds"
            control.progressDialog.update(int((inter - i) / inter * 100), new_display_dialog)

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

        # Get the progress of the item
        def get_progress(item):
            try:
                text = item['name']
                progress_parts = text.rsplit(" - ", 1)
                if len(progress_parts) == 2:
                    current = int(progress_parts[1].split("/")[0])
                else:
                    current = 0
            except Exception:
                current = 0
            return current

        # PERFORMANCE: Get MAL IDs (prefer API, fallback to mappings database)
        mal_ids = []
        for anime in results['anime']:
            # Try API response first
            mal_id = anime['show']['ids'].get('mal')

            # Fallback to mappings database if API doesn't have it
            if not mal_id:
                simkl_id = anime['show']['ids'].get('simkl')
                if simkl_id:
                    mappings = database.get_mappings(simkl_id, 'simkl_id')
                    mal_id = mappings.get('mal_id')

            if mal_id:
                mal_ids.append(int(mal_id))

        mal_id_dicts = [{'mal_id': mid} for mid in mal_ids]
        get_meta.collect_meta(mal_id_dicts)

        # PERFORMANCE: Batch fetch all pre-computed metadata in one query
        show_list = database.get_show_list(mal_ids) if mal_ids else {}

        # Fetch AniList data for all MAL IDs
        try:
            from resources.lib.endpoints.anilist import Anilist
            anilist_data = Anilist().get_anilist_by_mal_ids(mal_ids)
        except Exception:
            anilist_data = []

        # Build AniList lookup by MAL ID (ensure all keys and lookups are strings)
        anilist_by_mal_id = {str(item.get('idMal')): item for item in anilist_data if item.get('idMal')}

        # Pass AniList data and show_list to view functions
        def viewfunc(res):
            mal_id = str(res['show']['ids'].get('mal'))
            anilist_item = anilist_by_mal_id.get(mal_id)
            return self._base_next_up_view(res, show_list, anilist_res=anilist_item) if next_up else self._base_watchlist_status_view(res, show_list, anilist_res=anilist_item)

        all_results = list(map(viewfunc, results['anime']))

        if int(self.sort) == 0:  # anime_title
            all_results = sorted(all_results, key=lambda x: x['info']['title'])
        elif int(self.sort) == 1:    # user_rating
            all_results = sorted(all_results, key=lambda x: x['info']['user_rating'] or 0, reverse=True)
        elif int(self.sort) == 2:    # progress
            all_results = sorted(all_results, key=get_progress)
        elif int(self.sort) == 3:    # list_updated_at
            all_results = sorted(all_results, key=lambda x: x['info']['last_watched'] or "0", reverse=True)
        elif int(self.sort) == 4:    # last_added
            all_results.reverse()

        if int(self.order) == 1:
            all_results.reverse()

        return all_results

    @div_flavor
    def _base_watchlist_status_view(self, res, show_list=None, mal_dub=None, anilist_res=None):
        show_ids = res['show']['ids']
        anilist_id = show_ids.get('anilist')
        mal_id = show_ids.get('mal')
        kitsu_id = show_ids.get('kitsu')

        # Fallback to mappings database if API doesn't have MAL ID
        if not mal_id:
            simkl_id = show_ids.get('simkl')
            if simkl_id:
                mappings = database.get_mappings(simkl_id, 'simkl_id')
                mal_id = mappings.get('mal_id')

        if not mal_id:
            control.log(f"Mal ID not found for {show_ids}", 'warning')

        # Ensure mal_id is an integer for database consistency
        try:
            mal_id = int(mal_id) if mal_id else None
        except (ValueError, TypeError):
            mal_id = None

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        # PERFORMANCE: Get pre-computed data from batch query (no pickle!)
        if show_list and mal_id in show_list:
            show_data = show_list[mal_id]
            art_dict = show_data['art'] or {}
            info_dict = show_data['info'] or {}
        else:
            art_dict = {}
            info_dict = {}

        # Title logic: prefer Simkl, fallback to pre-computed, fallback to AniList
        if self.title_lang == 'english':
            title = res['show']['title']
            # Try to get english title from pre-computed data
            if info_dict.get('title'):
                title = info_dict.get('title')
        else:
            title = res['show']['title']
        if anilist_res:
            title = anilist_res.get('title', {}).get(self.title_lang) or anilist_res.get('title', {}).get('romaji') or title
        if title is None:
            title = ''

        # Add relation info (if available)
        if anilist_res and anilist_res.get('relationType'):
            title += ' [I]%s[/I]' % control.colorstr(anilist_res['relationType'], 'limegreen')

        # Plot/synopsis
        plot = None
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

        # Playcount
        playcount = None
        if res["total_episodes_count"] != 0 and res["watched_episodes_count"] == res["total_episodes_count"]:
            playcount = 1

        # Premiered/year
        premiered = None
        year = None
        if anilist_res and anilist_res.get('startDate'):
            start_date = anilist_res.get('startDate')
            if isinstance(start_date, dict):
                y = int(start_date.get('year', 0) or 0)
                m = int(start_date.get('month', 1) or 1)
                d = int(start_date.get('day', 1) or 1)
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
        unique_ids = {
            'anilist_id': str(anilist_id),
            'mal_id': str(mal_id),
            'kitsu_id': str(kitsu_id),
            **database.get_unique_ids(anilist_id, 'anilist_id'),
            **database.get_unique_ids(mal_id, 'mal_id'),
            **database.get_unique_ids(kitsu_id, 'kitsu_id')
        }

        # Art/Images - PERFORMANCE: Use pre-computed art_dict (no pickle!)
        simkl_image = f'https://wsrv.nl/?url=https://simkl.in/posters/{res["show"]["poster"]}_m.jpg'
        anilist_image = anilist_res['coverImage'].get('extraLarge') if anilist_res and anilist_res.get('coverImage') else None

        image = art_dict.get('icon') or art_dict.get('poster') or simkl_image or anilist_image
        poster = art_dict.get('poster') or simkl_image or anilist_image
        fanart = art_dict.get('fanart') or simkl_image or anilist_image
        banner = art_dict.get('banner') or (anilist_res.get('bannerImage') if anilist_res else None)

        info = {
            'UniqueIDs': unique_ids,
            'title': title,
            'plot': plot,
            'genre': genre,
            'studio': studio,
            'status': status,
            'duration': duration,
            'country': country,
            'mediatype': 'tvshow',
            'year': year if year else res['show']['year'],
            'last_watched': res['last_watched_at'],
            'user_rating': res['user_rating']
        }
        if info_rating:
            info['rating'] = info_rating
        if playcount:
            info['playcount'] = playcount
        if premiered:
            info['premiered'] = premiered
        if cast:
            info['cast'] = cast
        if trailer:
            info['trailer'] = trailer

        base = {
            "name": '%s - %d/%d' % (title, res["watched_episodes_count"], res["total_episodes_count"]),
            "url": f'watchlist_to_ep/{mal_id}/{res["watched_episodes_count"]}',
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

        if res["total_episodes_count"] == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)

    @div_flavor
    def _base_next_up_view(self, res, show_list=None, mal_dub=None, anilist_res=None):
        show_ids = res['show']['ids']
        anilist_id = show_ids.get('anilist')
        mal_id = show_ids.get('mal')
        kitsu_id = show_ids.get('kitsu')

        # Fallback to mappings database if API doesn't have MAL ID
        if not mal_id:
            simkl_id = show_ids.get('simkl')
            if simkl_id:
                mappings = database.get_mappings(simkl_id, 'simkl_id')
                mal_id = mappings.get('mal_id')

        # Ensure mal_id is an integer for database consistency
        try:
            mal_id = int(mal_id) if mal_id else None
        except (ValueError, TypeError):
            mal_id = None

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        # PERFORMANCE: Get pre-computed metadata from batch query (Seren-style, no pickle!)
        precomputed_info = None
        precomputed_cast = None
        art_dict = {}

        if show_list and mal_id in show_list:
            show_data = show_list[mal_id]
            art_dict = show_data['art'] or {}
            precomputed_info = show_data['info']
            precomputed_cast = show_data['cast']

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
            # Use Simkl title for next_up (no pickle needed)
            if next_up_meta.get('title'):
                title = '%s - %s' % (title, next_up_meta['title'])
            if next_up_meta.get('image'):
                image = next_up_meta['image']
            plot = next_up_meta.get('plot')
            aired = next_up_meta.get('aired')
        else:
            plot = aired = None

        # PERFORMANCE: Use pre-computed plot as fallback
        if not plot and precomputed_info:
            plot = precomputed_info.get('plot')

        info = {
            'UniqueIDs': {
                'anilist_id': str(anilist_id),
                'mal_id': str(mal_id),
                'kitsu_id': str(kitsu_id),
                **database.get_unique_ids(anilist_id, 'anilist_id'),
                **database.get_unique_ids(mal_id, 'mal_id'),
                **database.get_unique_ids(kitsu_id, 'kitsu_id')
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

        # PERFORMANCE: Add pre-computed cast if available
        if precomputed_cast:
            info['cast'] = precomputed_cast

        # PERFORMANCE: Use pre-computed artwork from art_dict (no pickle!)
        fanart = art_dict.get('fanart') or image

        base = {
            "name": title,
            "url": f'watchlist_to_ep/{mal_id}/{res["watched_episodes_count"]}',
            "image": image,
            "info": info,
            "fanart": fanart,
            "poster": poster
        }

        # Add extra Fanart.tv artwork from pre-computed art_dict
        if art_dict.get('landscape') or art_dict.get('thumb'):
            base['landscape'] = art_dict.get('landscape') or art_dict.get('thumb')
        if art_dict.get('clearart'):
            base['clearart'] = art_dict.get('clearart')
        if art_dict.get('clearlogo'):
            base['clearlogo'] = art_dict.get('clearlogo')

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
        r = client.get(f'{self._URL}/sync/all-items/anime/{status}', headers=self.__headers(), params=params)
        return r.json() if r else {}

    def update_list_status(self, mal_id, status):
        data = {
            "shows": [{
                "to": status,
                "ids": {
                    "mal": mal_id
                }
            }]
        }
        r = client.post(f'{self._URL}/sync/add-to-list', headers=self.__headers(), json_data=data)
        if r:
            r = r.json()
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
        r = client.post(f'{self._URL}/sync/history', headers=self.__headers(), json_data=data)
        if r:
            r = r.json()
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

        r = client.post(url, headers=self.__headers(), json_data=data)
        if r:
            r = r.json()
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
        r = client.post(f"{self._URL}/sync/history/remove", headers=self.__headers(), json_data=data)
        if r:
            r = r.json()
            if not r['not_found']['shows'] or not r['not_found']['movies']:
                return True
        return False
