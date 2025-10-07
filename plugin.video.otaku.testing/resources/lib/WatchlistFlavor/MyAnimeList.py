import re
import time
import random
import pickle

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
        api_info = database.get_info('MyAnimeList')
        client_id = api_info['client_id']

        data = {
            'client_id': client_id,
            'code': code,
            'code_verifier': code_verifier,
            'grant_type': 'authorization_code'
        }
        r = client.post(oauth_url, data=data)
        if not r:
            return
        res = r.json()

        self.token = res['access_token']
        user = client.get(f'{self._URL}/users/@me', headers=self.__headers(), params={'fields': 'name'})
        user = user.json()

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
        api_info = database.get_info('MyAnimeList')
        client_id = api_info['client_id']

        data = {
            'client_id': client_id,
            'grant_type': 'refresh_token',
            'refresh_token': control.getSetting('mal.refresh')
        }
        r = client.post(oauth_url, data=data)
        if not r:
            return
        res = r.json()
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
        sort_types = ['anime_title', 'list_score', "", 'list_updated_at', 'anime_start_date']
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
        r = client.get(url, headers=self.__headers(), params=params)
        results = r.json() if r else {}

        # Extract mal_ids and create a list of dictionaries with 'mal_id' keys
        mal_ids = [item['node']['id'] for item in results.get('data', [])]
        mal_id_dicts = [{'mal_id': mid} for mid in mal_ids]
        get_meta.collect_meta(mal_id_dicts)

        # Fetch AniList data for all MAL IDs
        try:
            from resources.lib.endpoints.anilist import Anilist
            anilist_data = Anilist().get_anilist_by_mal_ids(mal_ids)
        except Exception:
            anilist_data = []

        # Build AniList lookup by MAL ID
        anilist_by_mal_id = {item.get('idMal'): item for item in anilist_data if item.get('idMal')}

        # If sorting by anime_title and language is english, sort manually by english title.
        if self.__get_sort() == 'anime_title' and self.title_lang == 'english':
            results['data'].sort(key=lambda item: (item['node'].get('alternative_titles', {}).get('en') or item['node'].get('title')).lower())

        # If sorting by progress, sort manually by progress:
        if int(self.sort) == 2:
            results['data'].sort(key=lambda item: item['list_status']['num_episodes_watched'])

        # If order is descending, reverse the order.
        if int(self.order) == 1:
            results['data'].reverse()

        # Pass AniList data to view functions
        def viewfunc(res):
            mal_id = res['node']['id']
            anilist_item = anilist_by_mal_id.get(mal_id)
            return self._base_next_up_view(res, anilist_res=anilist_item) if next_up else self._base_watchlist_status_view(res, anilist_res=anilist_item)

        all_results = list(map(viewfunc, results['data']))
        all_results += self.handle_paging(results.get('paging', {}).get('next'), base_plugin_url, page)
        return all_results

    @div_flavor
    def _base_watchlist_status_view(self, res, mal_dub=None, anilist_res=None):
        mal_id = res['node']['id']
        if not mal_id:
            control.log(f"Mal ID not found for {mal_id}", level='warning')

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        # Title logic: prefer MAL, fallback to AniList
        title = res['node'].get('title')
        if self.title_lang == 'english':
            title = res['node']['alternative_titles'].get('en') or title
        if not title and anilist_res:
            title = anilist_res.get('title', {}).get(self.title_lang) or anilist_res.get('title', {}).get('romaji') or title
        if title is None:
            title = ''

        # Add relation info (if available)
        if anilist_res and anilist_res.get('relationType'):
            title += ' [I]%s[/I]' % control.colorstr(anilist_res['relationType'], 'limegreen')

        # Plot/synopsis
        plot = res['node'].get('synopsis')
        if not plot and anilist_res and anilist_res.get('description'):
            desc = anilist_res['description']
            desc = desc.replace('<i>', '[I]').replace('</i>', '[/I]')
            desc = desc.replace('<b>', '[B]').replace('</b>', '[/B]')
            desc = desc.replace('<br>', '[CR]')
            desc = desc.replace('\n', '')
            plot = desc

        # Genres
        genre = [x.get('name') for x in res['node'].get('genres', [])]
        if (not genre or not genre) and anilist_res:
            genre = anilist_res.get('genres')

        # Studios
        studio = [x.get('name') for x in res['node'].get('studios', [])]
        if (not studio or not studio) and anilist_res and anilist_res.get('studios'):
            # AniList studios may be list or dict
            if isinstance(anilist_res['studios'], list):
                studio = [s.get('name') for s in anilist_res['studios']] or studio
            elif isinstance(anilist_res['studios'], dict) and 'edges' in anilist_res['studios']:
                studio = [s['node'].get('name') for s in anilist_res['studios']['edges']] or studio

        # Status
        status = res['node'].get('status')
        if not status and anilist_res:
            status = anilist_res.get('status')

        # Duration
        duration = res['node'].get('average_episode_duration')
        if not duration and anilist_res and anilist_res.get('duration'):
            duration = anilist_res.get('duration') * 60 if isinstance(anilist_res.get('duration'), int) else anilist_res.get('duration')

        # Country
        country = None
        if anilist_res:
            country = [anilist_res.get('countryOfOrigin', '')]

        # Rating/score
        rating = res['node'].get('mean')
        info_rating = None
        if isinstance(rating, (float, int)) and rating:
            info_rating = {'score': rating}
        elif anilist_res and anilist_res.get('averageScore'):
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
        eps_watched = res['list_status']["num_episodes_watched"]
        eps = res['node']["num_episodes"]
        playcount = None
        if eps_watched == eps and eps != 0:
            playcount = 1

        # Premiered/year
        start_date = res['node'].get('start_date')
        premiered = None
        year = None
        if not start_date and anilist_res and anilist_res.get('startDate'):
            start_date = anilist_res.get('startDate')
        if start_date:
            if isinstance(start_date, dict):
                premiered = '{}-{:02}-{:02}'.format(
                    int(start_date.get('year', 0) or 0),
                    int(start_date.get('month', 1) or 1),
                    int(start_date.get('day', 1) or 1)
                )
                year = int(start_date.get('year', 0) or 0) if start_date.get('year') is not None else None
            else:
                premiered = str(start_date)
                try:
                    year = int(str(start_date)[:4])
                except Exception:
                    pass

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
        unique_ids = {'mal_id': str(mal_id)}
        if anilist_res and anilist_res.get('id'):
            unique_ids['anilist_id'] = str(anilist_res['id'])
            unique_ids.update(database.get_mapping_ids(anilist_res['id'], 'anilist_id'))
        unique_ids.update(database.get_mapping_ids(mal_id, 'mal_id'))

        # Art/Images
        show_meta = database.get_show_meta(mal_id)
        kodi_meta = pickle.loads(show_meta.get('art')) if show_meta else {}
        image = res['node']['main_picture'].get('large', res['node']['main_picture']['medium']) if res['node'].get('main_picture') else None
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
            'UniqueIDs': unique_ids,
            'title': title,           # Title
            'plot': plot,             # Plot/Synopsis
            'genre': genre,           # Genres
            'studio': studio,         # Studios
            'status': status,         # Status
            'duration': duration,     # Duration
            'country': country,       # Country
            'mediatype': 'tvshow',
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
        if trailer:
            info['trailer'] = trailer
        if anilist_res and anilist_res.get('countryOfOrigin'):
            info['mpaa'] = anilist_res.get('countryOfOrigin')
        elif res['node'].get('rating'):
            info['mpaa'] = res['node'].get('rating')

        base = {
            "name": f"{title} - {eps_watched}/{eps}",
            "url": f'watchlist_to_ep/{mal_id}/{eps_watched}',
            "image": image,
            "poster": poster,
            'fanart': fanart,
            "banner": banner,
            "info": info
        }

        # Extra art
        if kodi_meta.get('thumb'):
            base['landscape'] = random.choice(kodi_meta['thumb'])
        if kodi_meta.get('clearart'):
            base['clearart'] = random.choice(kodi_meta['clearart'])
        if kodi_meta.get('clearlogo'):
            base['clearlogo'] = random.choice(kodi_meta['clearlogo'])

        # Movie logic
        if res['node']['media_type'] == 'movie' and eps == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)

    @div_flavor
    def _base_next_up_view(self, res, mal_dub=None, anilist_res=None):
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
        r = client.get(url, headers=self.__headers(), params=params)
        results = r.json().get('my_list_status') if r else {}
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
        r = client.get(f'{self._URL}/users/@me/animelist', headers=self.__headers(), params=params)
        res = r.json() if r else {}
        paging = res.get('paging', {})
        data = res.get('data', [])
        while paging.get('next'):
            r = client.get(paging['next'], headers=self.__headers())
            res = r.json() if r else {}
            paging = res.get('paging', {})
            data += res.get('data', [])
        return data

    def update_list_status(self, mal_id, status):
        data = {
            "status": status,
        }
        r = client.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r and r.ok

    def update_num_episodes(self, mal_id, episode):
        data = {
            'num_watched_episodes': int(episode)
        }
        r = client.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r and r.ok

    def update_score(self, mal_id, score):
        data = {
            "score": score,
        }
        r = client.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r and r.ok

    def delete_anime(self, mal_id):
        r = client.delete(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers())
        return r and r.ok
