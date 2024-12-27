import pickle
import datetime
import time
import json

from functools import partial
from resources.lib.ui import utils, database, control
from resources.lib import indexers
from resources import jz
from resources.lib.ui import client


class KitsuAPI:
    def __init__(self):
        self.baseUrl = "https://kitsu.io/api/edge"

    def get_kitsu_id(self, mal_id):
        meta_ids = database.get_mappings(mal_id, 'mal_id')
        return meta_ids.get('kitsu_id')

    def get_anime_info(self, mal_id):
        kitsu_id = self.get_kitsu_id(mal_id)
        response = client.request(f'{self.baseUrl}/anime/{kitsu_id}')
        if response:
            return json.loads(response)['data']

    def get_episode_meta(self, kitsu_id):
        url = f'{self.baseUrl}/anime/{kitsu_id}/episodes'
        res_data = []
        page = 1
        while True:
            params = {
                'page[limit]': 20,
                'page[offset]': (page - 1) * 20
            }
            response = client.request(url, params=params)
            if response:
                res = json.loads(response)
                res_data.extend(res['data'])
                if 'next' not in res['links']:
                    break
                page += 1
                if page % 3 == 0:
                    time.sleep(2)
        return res_data

    @staticmethod
    def parse_episode_view(res, mal_id, season, poster, fanart, eps_watched, update_time, tvshowtitle, dub_data, filler_data, episodes=None):
        episode = res['attributes']['number']
        url = f"{mal_id}/{episode}"
        title = res['attributes'].get('canonicalTitle', f'Episode {episode}')
        image = res['attributes']['thumbnail']['original'] if res['attributes'].get('thumbnail') else poster
        info = {
            'UniqueIDs': {'mal_id': str(mal_id)},
            'title': title,
            'season': season,
            'episode': episode,
            'plot': res['attributes'].get('synopsis', 'No plot available'),
            'tvshowtitle': tvshowtitle,
            'mediatype': 'episode'
        }
        if eps_watched and int(eps_watched) >= episode:
            info['playcount'] = 1

        try:
            info['aired'] = res['attributes']['airdate']
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
            parsed['info']['title'] = f'Episode {episode}'
            parsed['info']['plot'] = None
        return parsed

    def process_episode_view(self, mal_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data):
        kitsu_id = self.get_kitsu_id(mal_id)
        if not kitsu_id:
            return []

        update_time = datetime.date.today().isoformat()
        result = self.get_anime_info(mal_id)
        if not result:
            return []

        title_list = [title for title in result['attributes']['titles'].values()]
        season = utils.get_season(title_list, mal_id)

        result_ep = self.get_episode_meta(kitsu_id)
        # kodi_episodes = kodi_meta['episodes']
        # if kodi_episodes:
        #     control.print(f"Kodi Episodes: {kodi_episodes}, Kitsu Episodes: {len(result_ep)}")
        #     if len(result_ep) != kodi_episodes:
        #         return []

        mapfunc = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data)
        all_results = sorted(list(map(mapfunc, result_ep)), key=lambda x: x['info']['episode'])

        if control.getBool('override.meta.api') and control.getBool('override.meta.notify'):
            control.notify("Kitsu", f'{tvshowtitle} Added to Database', icon=poster)
        return all_results

    def append_episodes(self, mal_id, episodes, eps_watched, poster, fanart, tvshowtitle, filler_data=None, dub_data=None):
        kitsu_id = self.get_kitsu_id(mal_id)
        if not kitsu_id:
            return []

        update_time = datetime.date.today().isoformat()
        last_updated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(episodes[0].get('last_updated'), '%Y-%m-%d')))
        diff = (datetime.datetime.today() - last_updated).days
        if diff > control.getInt('interface.check.updates'):
            result = self.get_episode_meta(kitsu_id)
            season = episodes[0]['season']
            mapfunc2 = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data, episodes=episodes)
            all_results = list(map(mapfunc2, result))
            control.notify("Kitsu", f'{tvshowtitle} Appended to Database', icon=poster)
        else:
            mapfunc1 = partial(indexers.parse_episodes, eps_watched=eps_watched, dub_data=dub_data)
            all_results = list(map(mapfunc1, episodes))
        return all_results

    def get_episodes(self, mal_id, show_meta):
        kitsu_id = self.get_kitsu_id(mal_id)
        if not kitsu_id:
            return []

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
                from resources.jz import anime_filler
                filler_data = anime_filler.get_data(kodi_meta['ename'])
                return self.append_episodes(mal_id, episodes, eps_watched, poster, fanart, tvshowtitle, filler_data, dub_data)
            return indexers.process_episodes(episodes, eps_watched, dub_data)

        if kodi_meta['episodes'] is None or kodi_meta['episodes'] > 99:
            from resources.jz import anime_filler
            filler_data = anime_filler.get_data(kodi_meta['ename'])
        else:
            filler_data = None
        return self.process_episode_view(mal_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data)

    def get_anime(self, filter_type, page):
        perpage = 25
        params = {
            "page[limit]": perpage,
            "page[offset]": (page - 1) * perpage,
            "filter[status]": filter_type
        }
        response = client.request(f'{self.baseUrl}/anime', params=params)
        if response:
            return json.loads(response)