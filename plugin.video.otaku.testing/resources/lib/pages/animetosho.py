import re
import pickle
import base64

from functools import partial
from bs4 import BeautifulSoup
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.ui import database, source_utils, client, control
from resources.lib import debrid
from resources.lib.indexers.simkl import SIMKLAPI
from resources.lib.endpoints import anidb


class Sources(BrowserBase):
    _BASE_URL = 'https://animetosho.org'

    def __init__(self):
        self.sources = []
        self.cached = []
        self.uncached = []
        self.anidb_id = None
        self.anidb_ep_id = None
        self.paging = control.getInt('animetosho.paging')

    def get_sources(self, show, mal_id, episode, status, media_type, rescrape):
        show_meta = database.get_show_meta(mal_id)
        if show_meta:
            meta_ids = pickle.loads(show_meta['meta_ids'])
            self.anidb_id = meta_ids.get('anidb_id')
            if not self.anidb_id:
                ids = SIMKLAPI().get_mapping_ids('mal', mal_id)
                if ids:
                    self.anidb_id = meta_ids['anidb_id'] = ids['anidb']
                    database.update_show_meta(mal_id, meta_ids, pickle.loads(show_meta['art']))
        if self.anidb_id:
            episode_meta = database.get_episode(mal_id, episode)
            if episode_meta:
                self.anidb_ep_id = episode_meta['anidb_ep_id']
            if not self.anidb_ep_id:
                anidb_meta = anidb.get_episode_meta(self.anidb_id)
                anidb_meta = {x: v for x, v in anidb_meta.items() if x.isdigit()}
                for anidb_ep in anidb_meta:
                    database.update_episode_column(mal_id, anidb_ep, 'anidb_ep_id', anidb_meta[anidb_ep]['anidb_id'])

        episode = episode.zfill(2)
        self.sources += self.process_animetosho_episodes(f'{self._BASE_URL}/episode/{self.anidb_ep_id}', None, episode, None)

        show = self._clean_title(show)
        if media_type != "movie":
            season = database.get_episode(mal_id)['season']
            season = str(season).zfill(2)
            episode = episode.zfill(2)
            query = f'{show} "- {episode}"'
        else:
            season = None
            query = show

        params = {
            'q': self._sphinx_clean(query),
            'qx': 1
        }
        if self.anidb_id:
            params['aids'] = self.anidb_id

        # Add paging using self.paging
        for page in range(1, self.paging + 1):
            params['page'] = page
            self.sources += self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, episode, season)

        if status == 'FINISHED':
            batch_terms = ["Batch", "Complete Series"]
            episodes = pickle.loads(database.get_show(mal_id)['kodi_meta'])['episodes']
            if episodes:
                episode_formats = [f'01-{episodes}', f'01~{episodes}', f'01 - {episodes}', f'01 ~ {episodes}']
            else:
                episode_formats = []
            batch_query = f'{show} ("' + '"|"'.join(batch_terms + episode_formats) + '")'
            params['q'] = self._sphinx_clean(batch_query)
            self.sources += self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, episode, season)

        show_lower = show.lower()
        if 'season' in show_lower:
            show_variations = re.split(r'season\s*\d+', show_lower)
            cleaned_variations = [self._sphinx_clean(var.strip() + ')') for var in show_variations if var.strip()]
            params['q'] = '|'.join(cleaned_variations)
        else:
            params['q'] = self._sphinx_clean(show)

        # Add paging using self.paging
        for page in range(1, self.paging + 1):
            params['page'] = page
            self.sources += self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, episode, season)

        # remove any duplicate sources
        self.append_cache_uncached_noduplicates()
        return {'cached': self.cached, 'uncached': self.uncached}

    def process_animetosho_episodes(self, url, params, episode, season):
        response = client.request(url, params=params)
        if response:
            html = response
            soup = BeautifulSoup(html, "html.parser")
            soup_all = soup.find('div', id='content').find_all('div', class_='home_list_entry')
            rex = r'(magnet:)+[^"]*'
            list_ = []
            for soup in soup_all:
                list_item = {
                    'name': soup.find('div', class_='link').a.text,
                    'magnet': soup.find('a', {'href': re.compile(rex)}).get('href'),
                    'size': soup.find('div', class_='size').text,
                    'downloads': 0,
                    'torrent': soup.find('a', class_='dllink').get('href')
                }
                try:
                    list_item['seeders'] = int(re.match(r'Seeders: (\d+)', soup.find('span', {'title': re.compile(r'Seeders')}).get('title')).group(1))
                except AttributeError:
                    list_item['seeders'] = -1

                # Extract hash
                try:
                    list_item['hash'] = re.match(r'https://animetosho.org/storage/torrent/([^/]+)', list_item['torrent']).group(1)
                except AttributeError:
                    try:
                        hash_32 = re.search(r'btih:(\w+)&tr=http', list_item['magnet']).group(1)
                        list_item['hash'] = base64.b16encode(base64.b32decode(hash_32)).decode().lower()
                    except AttributeError:
                        continue  # Skip this list item if no valid hash is found

                list_.append(list_item)

            if season:
                filtered_list = source_utils.filter_sources('animetosho', list_, int(season), int(episode), anidb_id=self.anidb_id)
            else:
                filtered_list = list_

            cache_list, uncashed_list_ = debrid.torrentCacheCheck(filtered_list)
            uncashed_list = [i for i in uncashed_list_ if i['seeders'] != 0]

            uncashed_list = sorted(uncashed_list, key=lambda k: k['seeders'], reverse=True)
            cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)

            mapfunc = partial(parse_animetosho_view, episode=episode)
            all_results = list(map(mapfunc, cache_list))
            if control.settingids.showuncached:
                mapfunc2 = partial(parse_animetosho_view, episode=episode, cached=False)
                all_results += list(map(mapfunc2, uncashed_list))
            return all_results
        return []

    def append_cache_uncached_noduplicates(self):
        seen_sources = []
        for source in self.sources:
            if source not in seen_sources:
                seen_sources.append(source)
                if source['cached']:
                    self.cached.append(source)
                else:
                    self.uncached.append(source)


def parse_animetosho_view(res, episode, cached=True):
    source = {
        'release_title': res['name'],
        'hash': res['hash'],
        'type': 'torrent',
        'quality': source_utils.getQuality(res['name']),
        'debrid_provider': res.get('debrid_provider'),
        'provider': 'animetosho',
        'episode_re': episode,
        'size': res['size'],
        'info': source_utils.getInfo(res['name']),
        'byte_size': 0,
        'lang': source_utils.getAudio_lang(res['name']),
        'channel': source_utils.getAudio_channel(res['name']),
        'sub': source_utils.getSubtitle_lang(res['name']),
        'cached': cached,
        'seeders': res['seeders'],
    }

    match = re.match(r'(\d+).(\d+) (\w+)', res['size'])
    if match:
        source['byte_size'] = source_utils.convert_to_bytes(float(f'{match.group(1)}.{match.group(2)}'), match.group(3))
    if not cached:
        source['magnet'] = res['magnet']
        source['type'] += ' (uncached)'
    return source
