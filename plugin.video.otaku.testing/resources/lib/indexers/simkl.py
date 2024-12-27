import pickle
import datetime
import time
import json

from functools import partial
from resources.lib.ui import database, utils, control, client
from resources.lib import indexers
from resources import jz


class SIMKLAPI:
    def __init__(self):
        # self.ClientID = "5178a709b7942f1f5077b737b752eea0f6dee684d0e044fa5acee8822a0cbe9b" # Swag API Key
        # self.ClientID = "503b6b37476926a7a17ac86b95a81b245879955a7531e3e7d8913c0624796ea0" # My API key

        self.ClientID = "59dfdc579d244e1edf6f89874d521d37a69a95a1abd349910cb056a1872ba2c8"  # Otaku API key
        self.baseUrl = "https://api.simkl.com"
        self.imagePath = "https://wsrv.nl/?url=https://simkl.in/episodes/%s_w.webp"

    def parse_episode_view(self, res, mal_id, season, poster, fanart, eps_watched, update_time, tvshowtitle, dub_data, filler_data, episodes=None):
        episode = int(res['episode'])
        url = f"{mal_id}/{episode}"
        title = res.get('title')
        if not title:
            title = f'Episode {episode}'
        image = self.imagePath % res['img'] if res.get('img') else poster
        info = {
            'UniqueIDs': {'mal_id': str(mal_id)},
            'plot': res.get('description', 'No plot available'),
            'title': title,
            'season': season,
            'episode': episode,
            'tvshowtitle': tvshowtitle,
            'mediatype': 'episode'
        }
        if eps_watched and int(eps_watched) >= episode:
            info['playcount'] = 1

        try:
            info['aired'] = res['date'][:10]
        except (KeyError, TypeError):
            pass

        try:
            filler = filler_data[episode - 1]
        except (IndexError, TypeError):
            filler = ''
        code = jz.get_second_label(info, dub_data)
        if not code and control.settingids.filler:
            filler = code = control.colorstr(filler, color="red") if filler == 'Filler' else filler
        info['code'] = code

        parsed = utils.allocate_item(title, f"play/{url}", False, True, [], image, info, fanart, poster)
        kodi_meta = pickle.dumps(parsed)
        if not episodes or kodi_meta != episodes[episode - 1]['kodi_meta']:
            database.update_episode(mal_id, season, episode, update_time, kodi_meta, filler)

        if control.settingids.clean_titles and info.get('playcount') != 1:
            parsed['info']['title'] = f'Episode {res["episode"]}'
            parsed['info']['plot'] = None
        return parsed

    def process_episode_view(self, mal_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data):
        update_time = datetime.date.today().isoformat()
        result = self.get_anime_info(mal_id)
        if not result:
            return []

        title_list = [name['name'] for name in result.get('alt_titles', [])]
        season = utils.get_season(title_list, mal_id) if int(result.get('season', 1)) == 1 else int(result['season'])
        result_meta = self.get_episode_meta(mal_id)

        result_ep = [x for x in result_meta if x['type'] == 'episode']
        # kodi_episodes = kodi_meta['episodes']
        # if kodi_episodes:
        #     control.print(f"Kodi Episodes: {kodi_episodes}, SIMKL Episodes: {len(result_ep)}")
        #     if len(result_ep) != kodi_episodes:
        #         return []

        mapfunc = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data)
        all_results = list(map(mapfunc, result_ep))

        if control.getBool('override.meta.api') and control.getBool('override.meta.notify'):
            control.notify("SIMKL", f'{tvshowtitle} Added to Database', icon=poster)
        return all_results

    def append_episodes(self, mal_id, episodes, eps_watched, poster, fanart, tvshowtitle, dub_data=None):
        update_time = datetime.date.today().isoformat()
        last_updated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(episodes[0].get('last_updated'), '%Y-%m-%d')))
        diff = (datetime.datetime.today() - last_updated).days

        if diff >= control.getInt('interface.check.updates'):
            result_meta = self.get_episode_meta(mal_id)
            result_ep = [x for x in result_meta if x['type'] == 'episode']
            season = episodes[0]['season']
            mapfunc2 = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=None, episodes=episodes)
            all_results = list(map(mapfunc2, result_ep))
            control.notify("SIMKL Appended", f'{tvshowtitle} Appended to Database', icon=poster)
        else:
            database.update_episode(mal_id, episodes[0]['season'], episodes[0]['number'], update_time, episodes[0]['kodi_meta'], episodes[0]['filler'])
            mapfunc1 = partial(indexers.parse_episodes, eps_watched=eps_watched, dub_data=dub_data)
            all_results = list(map(mapfunc1, episodes))
        return all_results

    def get_episodes(self, mal_id, show_meta):
        kodi_meta = pickle.loads(database.get_show(mal_id)['kodi_meta'])
        kodi_meta.update(pickle.loads(show_meta['art']))
        fanart = kodi_meta.get('fanart')
        poster = kodi_meta.get('poster')
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
                return self.append_episodes(mal_id, episodes, eps_watched, poster, fanart, tvshowtitle, dub_data)
            return indexers.process_episodes(episodes, eps_watched, dub_data)
        if kodi_meta['episodes'] is None or kodi_meta['episodes'] > 99:
            from resources.jz import anime_filler
            filler_data = anime_filler.get_data(kodi_meta['ename'])
        else:
            filler_data = None
        return self.process_episode_view(mal_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data)

    def get_anime_info(self, mal_id):
        show_ids = database.get_show(mal_id)
        if not (simkl_id := show_ids['simkl_id']):
            simkl_id = self.get_id('mal', mal_id)
            database.add_mapping_id(mal_id, 'simkl_id', simkl_id)

        params = {
            'extended': 'full',
            'client_id': self.ClientID
        }
        response = client.request(f'{self.baseUrl}/anime/{simkl_id}', params=params)
        if response:
            return json.loads(response)
        return {}

    def get_episode_meta(self, mal_id):
        show_ids = database.get_show(mal_id)
        simkl_id = show_ids['simkl_id']
        if not simkl_id:
            mal_id = show_ids['mal_id']
            simkl_id = self.get_id('mal', mal_id)
            database.add_mapping_id(mal_id, 'simkl_id', simkl_id)
        params = {
            'extended': 'full',
            'client_id': self.ClientID
        }
        response = client.request(f'{self.baseUrl}/anime/episodes/{simkl_id}', params=params)
        if response:
            return json.loads(response)
        return {}

    def get_id(self, send_id, anime_id):
        params = {
            send_id: anime_id,
            "client_id": self.ClientID,
        }
        response = client.request(f'{self.baseUrl}/search/id', params=params)
        if response:
            r = json.loads(response)
            if r:
                anime_id = r[0]['ids']['simkl']
                return anime_id

    def get_mapping_ids(self, send_id, anime_id):
        # return_id = anidb, ann, mal, offjp, wikien, wikijp, instagram, imdb, tmdb, tw, tvdbslug, anilist, animeplanet, anisearch, kitsu, livechart, traktslug
        simkl_id = self.get_id(send_id, anime_id)
        params = {
            'extended': 'full',
            'client_id': self.ClientID
        }
        response = client.request(f'{self.baseUrl}/anime/{simkl_id}', params=params)
        if response:
            r = json.loads(response)
            return r['ids']