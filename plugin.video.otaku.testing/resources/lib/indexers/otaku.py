import pickle
import datetime
import time
import random

from functools import partial
from resources.lib.ui import utils, database, client, control
from resources.lib import indexers


class OtakuAPI:
    def __init__(self):
        self.baseUrl = "https://api.jikan.moe/v4"
        # Simkl API setup
        api_info = database.get_info('Simkl')
        self.simklClientID = api_info['client_id']
        self.simklBaseUrl = "https://api.simkl.com"
        self.simklImagePath = "https://wsrv.nl/?url=https://simkl.in/episodes/%s_w.webp"
        # AniDB API setup
        anidb_info = database.get_info('AniDB')
        self.anidbClientName = anidb_info['client_id']
        self.anidbBaseUrl = 'http://api.anidb.net:9001/httpapi'
        # AniZip API setup
        self.anizipBaseUrl = "https://api.ani.zip"
        # Kitsu API setup
        self.kitsuBaseUrl = "https://kitsu.io/api/edge"

    def get_kitsu_id(self, mal_id):
        meta_ids = database.get_mappings(mal_id, 'mal_id')
        return meta_ids.get('kitsu_id')

    def get_kitsu_episode_meta(self, mal_id):
        kitsu_id = self.get_kitsu_id(mal_id)
        url = f'{self.kitsuBaseUrl}/anime/{kitsu_id}/episodes'
        res_data = []
        page = 1
        while True:
            params = {
                'page[limit]': 20,
                'page[offset]': (page - 1) * 20
            }
            response = client.get(url, params=params)
            if response:
                res = response.json()
                res_data.extend(res['data'])
                if 'next' not in res['links']:
                    break
                page += 1
                if page % 3 == 0:
                    time.sleep(2)
        return res_data

    def get_anizip_episode_meta(self, mal_id):
        params = {
            'mal_id': mal_id
        }
        response = client.get(f'{self.anizipBaseUrl}/mappings', params=params)
        episodes = []
        if response:
            result = response.json()
            if 'episodes' in result:
                for res in result['episodes']:
                    if str(res).isdigit():
                        ep = result['episodes'][res]
                        episodes.append(ep)
        return episodes

    def get_anidb_id(self, mal_id):
        meta_ids = database.get_mappings(mal_id, 'mal_id')
        return meta_ids.get('anidb_id')

    def get_anidb_episode_meta(self, mal_id):
        import time
        anidb_id = self.get_anidb_id(mal_id)
        # Rate limit: ensure at least 4 seconds between requests
        last_request = control.getInt('anidb_last_request')
        now = int(time.time())
        if last_request > 0:
            elapsed = now - last_request
            if elapsed < 4:
                time.sleep(4 - elapsed)
        params = {
            'request': 'anime',
            'client': self.anidbClientName,
            'clientver': 1,
            'protover': 1,
            'aid': anidb_id
        }
        response = client.get(self.anidbBaseUrl, params=params)
        control.setInt('anidb_last_request', int(time.time()))
        episodes = []
        if response:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            for ep in root.findall('.//episode'):
                epno_text = ep.find('epno').text
                if epno_text is None:
                    continue
                try:
                    episode_num = int(epno_text)
                except ValueError:
                    continue
                title_elem = ep.find("title[@{http://www.w3.org/XML/1998/namespace}lang='en']")
                title_val = title_elem.text if title_elem is not None else f"Episode {episode_num}"
                rating_elem = ep.find('rating')
                if rating_elem is not None:
                    rating_val = rating_elem.text
                    votes_val = rating_elem.get('votes')
                else:
                    rating_val = None
                    votes_val = None
                episodes.append({
                    'type': 'episode',
                    'episode': episode_num,
                    'anidb_id': ep.get('id'),
                    'title': title_val,
                    'airdate': ep.find('airdate').text if ep.find('airdate') is not None else '',
                    'summary': ep.find('summary').text if ep.find('summary') is not None else '',
                    'rating': rating_val,
                    'votes': votes_val,
                })
        return episodes

    def get_simkl_id(self, mal_id):
        show_ids = database.get_show(mal_id)
        if not (simkl_id := show_ids.get('simkl_id')):
            params = {
                'mal': mal_id,
                'client_id': self.simklClientID
            }
            response = client.get(f'{self.simklBaseUrl}/search/id', params=params)
            if response:
                r = response.json()
                if r:
                    simkl_id = r[0]['ids']['simkl']
                    database.add_mapping_id(mal_id, 'simkl_id', simkl_id)
        return simkl_id

    def get_simkl_episode_meta(self, mal_id):
        simkl_id = self.get_simkl_id(mal_id)
        params = {
            'extended': 'full',
            'client_id': self.simklClientID
        }
        response = client.get(f'{self.simklBaseUrl}/anime/episodes/{simkl_id}', params=params)
        if response:
            return response.json()
        return []

    def get_anime_info(self, mal_id):
        response = client.get(f'{self.baseUrl}/anime/{mal_id}')
        if response:
            return response.json()['data']

    def get_episode_meta(self, mal_id):
        url = f'{self.baseUrl}/anime/{mal_id}/episodes'
        response = client.get(url)
        if response:
            res = response.json()
            if not res['pagination']['has_next_page']:
                res_data = res['data']
            else:
                res_data = res['data']
                for i in range(2, res['pagination']['last_visible_page'] + 1):
                    params = {
                        'page': i
                    }
                    response = client.get(url, params=params)
                    if response:
                        r = response.json()
                        if not r['pagination']['has_next_page']:
                            res_data += r['data']
                            break
                        res_data += r['data']
                        if i % 3 == 0:
                            time.sleep(2)
        return res_data

    def parse_episode_view(self, res, mal_id, season, poster, fanart, clearart, clearlogo, eps_watched, update_time, tvshowtitle, dub_data, filler_data, episodes=None, meta_cache=None):
        episode_num = str(res.get('episode', res.get('mal_id')))
        # Use cached meta lists
        anidb_meta_list = meta_cache.get('anidb') if meta_cache else None
        simkl_meta_list = meta_cache.get('simkl') if meta_cache else None
        jikan_meta_list = meta_cache.get('jikan') if meta_cache else None
        anizip_meta_list = meta_cache.get('anizip') if meta_cache else None
        kitsu_meta_list = meta_cache.get('kitsu') if meta_cache else None

        # Find episode meta for this episode
        anidb_meta = None
        if anidb_meta_list:
            for ep in anidb_meta_list:
                if str(ep.get('episode')) == episode_num:
                    anidb_meta = ep
                    break
        simkl_meta = None
        if simkl_meta_list:
            for ep in simkl_meta_list:
                if str(ep.get('episode')) == episode_num:
                    simkl_meta = ep
                    break
        jikan_meta = None
        if jikan_meta_list:
            for ep in jikan_meta_list:
                if str(ep.get('mal_id', ep.get('episode'))) == episode_num:
                    jikan_meta = ep
                    break
        anizip_meta = None
        if anizip_meta_list:
            for ep in anizip_meta_list:
                if str(ep.get('episode')) == episode_num:
                    anizip_meta = ep
                    break
        kitsu_meta = None
        if kitsu_meta_list:
            for ep in kitsu_meta_list:
                if str(ep.get('attributes', {}).get('number')) == episode_num:
                    kitsu_meta = ep
                    break

        kodi_meta = pickle.loads(database.get_show(mal_id)['kodi_meta'])
        episode = res.get('mal_id', res.get('episode'))
        url = f"{mal_id}/{episode}"
        # Fallback logic for title
        title = (
            (anidb_meta.get('title') if anidb_meta else None)
            or (simkl_meta.get('title') if simkl_meta else None)
            or (jikan_meta.get('title') if jikan_meta else None)
            or (anizip_meta['title']['en'] if anizip_meta and anizip_meta.get('title') and 'en' in anizip_meta['title'] else None)
            or (kitsu_meta['attributes'].get('canonicalTitle') if kitsu_meta and kitsu_meta.get('attributes') and kitsu_meta['attributes'].get('canonicalTitle') else None)
            or res.get('title')
            or res.get('episode')
            or f"Episode {episode}"
        )
        # Fallback logic for image (AniDB does not provide images)
        image = (
            (self.simklImagePath % simkl_meta['img'] if simkl_meta and simkl_meta.get('img') else None)
            or (anizip_meta['image'] if anizip_meta and anizip_meta.get('image') else None)
            or (kitsu_meta['attributes']['thumbnail']['original'] if kitsu_meta and kitsu_meta.get('attributes') and kitsu_meta['attributes'].get('thumbnail') and kitsu_meta['attributes']['thumbnail'].get('original') else None)
            or poster
        )
        # Fallback logic for plot
        plot = (
            (anidb_meta.get('summary') if anidb_meta else None)
            or (simkl_meta.get('description') if simkl_meta else None)
            or (jikan_meta.get('synopsis') if jikan_meta else None)
            or (anizip_meta.get('overview') if anizip_meta else None)
            or (kitsu_meta['attributes'].get('synopsis') if kitsu_meta and kitsu_meta.get('attributes') and kitsu_meta['attributes'].get('synopsis') else None)
            or 'No plot available'
        )
        info = {
            'UniqueIDs': {
                'mal_id': str(mal_id),
                **database.get_mapping_ids(mal_id, 'mal_id')
            },
            'title': title,
            'season': season,
            'episode': episode,
            'plot': plot,
            'tvshowtitle': tvshowtitle,
            'mediatype': 'episode',
            'status': kodi_meta.get('status'),
            'genre': kodi_meta.get('genre'),
            'country': kodi_meta.get('country'),
            'cast': kodi_meta.get('cast'),
            'studio': kodi_meta.get('studio'),
            'mpaa': kodi_meta.get('mpaa'),
        }

        if eps_watched and int(eps_watched) >= episode:
            info['playcount'] = 1

        # Fallback logic for rating
        rating = None
        try:
            rating = float(anidb_meta.get('rating')) if anidb_meta and anidb_meta.get('rating') else None
        except Exception:
            pass
        if rating is None and simkl_meta and simkl_meta.get('rating'):
            try:
                rating = float(simkl_meta['rating'])
            except Exception:
                pass
        if rating is None and jikan_meta and jikan_meta.get('score'):
            try:
                rating = float(jikan_meta['score'])
            except Exception:
                pass
        if rating is None and anizip_meta and anizip_meta.get('rating'):
            try:
                rating = float(anizip_meta['rating'])
            except Exception:
                pass
        if rating is None and kitsu_meta and kitsu_meta.get('attributes') and kitsu_meta['attributes'].get('rating'):
            try:
                rating = float(kitsu_meta['attributes']['rating'])
            except Exception:
                pass
        if rating is not None:
            info['rating'] = {'score': rating}

        # Fallback logic for aired date
        aired = None
        try:
            aired = anidb_meta.get('airdate')[:10] if anidb_meta and anidb_meta.get('airdate') else None
        except Exception:
            pass
        if not aired and simkl_meta and simkl_meta.get('date'):
            aired = simkl_meta['date'][:10]
        if not aired and jikan_meta and jikan_meta.get('aired'):
            aired = jikan_meta['aired'][:10]
        if not aired and anizip_meta and anizip_meta.get('airDate'):
            aired = anizip_meta['airDate'][:10]
        if not aired and kitsu_meta and kitsu_meta.get('attributes') and kitsu_meta['attributes'].get('airdate'):
            aired = kitsu_meta['attributes']['airdate']
        if aired:
            info['aired'] = aired

        try:
            filler = filler_data[episode - 1]
        except (IndexError, TypeError):
            filler = ''

        parsed = indexers.update_database(mal_id, update_time, res, url, image, info, season, episode, episodes, title, fanart, poster, clearart, clearlogo, dub_data, filler)
        return parsed

    def process_episode_view(self, mal_id, poster, fanart, clearart, clearlogo, eps_watched, tvshowtitle, dub_data, filler_data):
        update_time = datetime.date.today().isoformat()
        result = self.get_anime_info(mal_id)
        if not result:
            return []

        title_list = [name['title'] for name in result['titles']]
        season = utils.get_season(title_list, mal_id)

        # Fetch all episode meta once per API
        import threading
        meta_cache = {}

        def fetch_anidb():
            meta_cache['anidb'] = self.get_anidb_episode_meta(mal_id)

        def fetch_simkl():
            simkl_raw = self.get_simkl_episode_meta(mal_id)
            meta_cache['simkl'] = [x for x in simkl_raw if x.get('type') == 'episode'] if isinstance(simkl_raw, list) else []

        def fetch_jikan():
            meta_cache['jikan'] = self.get_episode_meta(mal_id)

        def fetch_anizip():
            meta_cache['anizip'] = self.get_anizip_episode_meta(mal_id)

        def fetch_kitsu():
            meta_cache['kitsu'] = self.get_kitsu_episode_meta(mal_id)

        threads = [
            threading.Thread(target=fetch_anidb),
            threading.Thread(target=fetch_simkl),
            threading.Thread(target=fetch_jikan),
            threading.Thread(target=fetch_anizip),
            threading.Thread(target=fetch_kitsu)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Use AniDB as base, fallback to Simkl, then Jikan
        base_ep_list = meta_cache['anidb'] if meta_cache['anidb'] else meta_cache['simkl'] if meta_cache['simkl'] else meta_cache['jikan']
        mapfunc = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, clearart=clearart, clearlogo=clearlogo, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data, meta_cache=meta_cache)
        all_results = sorted(list(map(mapfunc, base_ep_list)), key=lambda x: x['info']['episode'])

        if control.getBool('override.meta.api') and control.getBool('override.meta.notify'):
            control.notify("Otaku", f'{tvshowtitle} Added to Database', icon=poster)
        return all_results

    def append_episodes(self, mal_id, episodes, eps_watched, poster, fanart, clearart, clearlogo, tvshowtitle, filler_data=None, dub_data=None):
        update_time, diff = indexers.get_diff(episodes[-1])
        if diff > control.getInt('interface.check.updates'):
            result = self.get_episode_meta(mal_id)
            season = episodes[0]['season']
            mapfunc2 = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, clearart=clearart, clearlogo=clearlogo, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data, episodes=episodes)
            all_results = list(map(mapfunc2, result))
        else:
            mapfunc1 = partial(indexers.parse_episodes, eps_watched=eps_watched, dub_data=dub_data)
            all_results = list(map(mapfunc1, episodes))
        return all_results

    def get_episodes(self, mal_id, show_meta):
        kodi_meta = pickle.loads(database.get_show(mal_id)['kodi_meta'])
        kodi_meta.update(pickle.loads(show_meta['art']))
        fanart = kodi_meta.get('fanart')
        poster = kodi_meta.get('poster')
        clearart = random.choice(kodi_meta['clearart']) if kodi_meta.get('clearart') else ''
        clearlogo = random.choice(kodi_meta['clearlogo']) if kodi_meta.get('clearlogo') else ''
        tvshowtitle = kodi_meta['title_userPreferred']
        if not (eps_watched := kodi_meta.get('eps_watched')) and control.settingids.watchlist_data:
            from resources.lib.WatchlistFlavor import WatchlistFlavor
            flavor = WatchlistFlavor.get_update_flavor()
            if flavor and flavor.flavor_name in control.enabled_watchlists():
                data = flavor.get_watchlist_anime_entry(mal_id)
                if data.get('eps_watched'):
                    eps_watched = kodi_meta['eps_watched'] = data['eps_watched']
                    database.update_kodi_meta(mal_id, kodi_meta)
        episodes = database.get_episode_list(mal_id)
        dub_data = indexers.process_dub(mal_id, kodi_meta['ename']) if control.getBool('jz.dub') else None
        if episodes:
            if kodi_meta['status'] not in ["FINISHED", "Finished Airing"]:
                from resources.lib.endpoints import anime_filler
                filler_data = anime_filler.get_data(kodi_meta['ename'])
                return self.append_episodes(mal_id, episodes, eps_watched, poster, fanart, clearart, clearlogo, tvshowtitle, filler_data, dub_data)
            return indexers.process_episodes(episodes, eps_watched, dub_data)

        if kodi_meta['episodes'] is None or kodi_meta['episodes'] > 99:
            from resources.lib.endpoints import anime_filler
            filler_data = anime_filler.get_data(kodi_meta['ename'])
        else:
            filler_data = None
        return self.process_episode_view(mal_id, poster, fanart, clearart, clearlogo, eps_watched, tvshowtitle, dub_data, filler_data)

    def get_anime(self, filter_type, page):
        perpage = 25
        params = {
            "limit": perpage,
            "page": page,
            "filter": filter_type
        }
        response = client.get(f'{self.baseUrl}/top/anime', params=params)
        if response:
            return response.json()
