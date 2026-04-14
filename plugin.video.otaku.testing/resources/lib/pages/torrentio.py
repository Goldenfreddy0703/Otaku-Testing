import re

from functools import partial
from resources.lib.ui import database, source_utils, control, client, utils
from resources.lib.ui.BrowserBase import BrowserBase


class Sources(BrowserBase):
    _BASE_URL = 'https://torrentio.strem.fun'

    def __init__(self):
        self.media_type = None
        self.cached = []
        self.uncached = []
        self.sources = []
        self.kitsu_id = None

    def _build_config(self):
        providers = control.getStringList('torrentio.config')
        config = {
            'providers': ','.join(providers) if providers else ''
        }
        
        if not control.getBool('show.uncached'):
            config['debridoptions'] = 'nodownloadlinks'

        enabled_debrids = control.enabled_debrid()
        if enabled_debrids.get('realdebrid'):
            token = control.getSetting('realdebrid.token')
            if token:
                config['realdebrid'] = token
        if enabled_debrids.get('debridlink'):
            token = control.getSetting('debridlink.token')
            if token:
                config['debridlink'] = token
        if enabled_debrids.get('alldebrid'):
            token = control.getSetting('alldebrid.token')
            if token:
                config['alldebrid'] = token
        if enabled_debrids.get('premiumize'):
            token = control.getSetting('premiumize.token')
            if token:
                config['premiumize'] = token
        if enabled_debrids.get('torbox'):
            token = control.getSetting('torbox.token')
            if token:
                config['torbox'] = token
        if enabled_debrids.get('easydebrid'):
            token = control.getSetting('easydebrid.token')
            if token:
                config['easydebrid'] = token

        return config

    def _config_url(self):
        config = self._build_config()
        return "|".join([f"{k}={v}" for k, v in config.items()])

    def get_sources(self, query, mal_id, episode, status, media_type, season=None, part=None):
        self.media_type = media_type

        show_ids = database.get_mappings(mal_id, 'mal_id')
        if show_ids:
            self.kitsu_id = show_ids.get('kitsu_id')

        if not self.kitsu_id:
            control.log('Torrentio: No kitsu_id found, skipping', 'warning')
            return {'cached': [], 'uncached': []}

        if media_type == 'movie':
            return self.get_movie_sources(mal_id)

        episode_zfill = episode.zfill(2)
        self.sources = self.process_torrentio_episodes(mal_id, episode_zfill)

        self.append_cache_uncached_noduplicates()
        return {'cached': self.cached, 'uncached': self.uncached}

    def get_movie_sources(self, mal_id):
        self.sources = self.process_torrentio_movie(mal_id)

        self.append_cache_uncached_noduplicates()
        return {'cached': self.cached, 'uncached': self.uncached}

    def process_torrentio_episodes(self, mal_id, episode):
        config_str = self._config_url()
        url = f"{self._BASE_URL}/{config_str}/stream/series/kitsu:{self.kitsu_id}:{episode}.json"
        control.log(f"Torrentio: Fetching episode sources from kitsu:{self.kitsu_id}:{episode}")

        response = client.get(url, timeout=30)
        if response:
            data = response.json()
            if not data:
                return []

            list_ = self._parse_stream_list(data)
            control.log(f"Torrentio: Got {len(list_)} raw streams")

            # Torrentio already returns debrid-checked results, split cached/uncached
            cache_list = [i for i in list_ if i['cached']]
            uncached_list = [i for i in list_ if not i['cached'] and i['seeders'] > 0]

            cache_list = sorted(cache_list, key=lambda k: k['seeders'], reverse=True)
            uncached_list = sorted(uncached_list, key=lambda k: k['seeders'], reverse=True)

            mapfunc = partial(self.parse_torrentio_view, episode=episode)
            all_results = utils.parallel_process(cache_list, mapfunc) if cache_list else []
            if control.getBool('show.uncached') and uncached_list:
                mapfunc2 = partial(self.parse_torrentio_view, episode=episode, cached=False)
                all_results += utils.parallel_process(uncached_list, mapfunc2)
            return all_results
        return []

    def process_torrentio_movie(self, mal_id):
        config_str = self._config_url()
        url = f"{self._BASE_URL}/{config_str}/stream/movie/kitsu:{self.kitsu_id}.json"
        control.log(f"Torrentio: Fetching movie sources from kitsu:{self.kitsu_id}")

        response = client.get(url, timeout=30)
        if response:
            data = response.json()
            if not data:
                return []

            list_ = self._parse_stream_list(data)
            control.log(f"Torrentio: Got {len(list_)} raw movie streams")

            cache_list = [i for i in list_ if i['cached']]
            uncached_list = [i for i in list_ if not i['cached'] and i['seeders'] > 0]

            cache_list = sorted(cache_list, key=lambda k: k['seeders'], reverse=True)
            uncached_list = sorted(uncached_list, key=lambda k: k['seeders'], reverse=True)

            mapfunc = partial(self.parse_torrentio_view, episode='1')
            all_results = utils.parallel_process(cache_list, mapfunc) if cache_list else []
            if control.getBool('show.uncached') and uncached_list:
                mapfunc2 = partial(self.parse_torrentio_view, episode='1', cached=False)
                all_results += utils.parallel_process(uncached_list, mapfunc2)
            return all_results
        return []

    @staticmethod
    def _parse_stream_list(data):
        re_hash = re.compile(r'(?<=/)([a-f0-9]{40})(?=/)')
        re_seeders = re.compile(r'👤\s*(\d+)')
        re_provider = re.compile(r'⚙️\s*(\w+)')

        list_ = []
        for stream in data.get('streams', []):
            behaviorhints = stream.get('behaviorHints', {})
            match_seeders = re_seeders.search(stream.get('title', ''))
            match_provider = re_provider.search(stream.get('title', ''))

            try:
                match_hash = re_hash.search(stream.get('url', ''))
                torrent_hash = match_hash.group(1)
            except (AttributeError, IndexError):
                torrent_hash = ''

            name = stream.get('name', '')
            cached = 'download' not in name.lower()

            if 'TB' in name:
                debrid_provider = 'TorBox'
            elif 'RD' in name:
                debrid_provider = 'Real-Debrid'
            elif 'DL' in name:
                debrid_provider = 'Debrid-Link'
            elif 'PR' in name:
                debrid_provider = 'Premiumize'
            elif 'AD' in name:
                debrid_provider = 'Alldebrid'
            elif 'ED' in name:
                debrid_provider = 'EasyDebrid'
            else:
                debrid_provider = 'Unknown'

            list_.append({
                'name': stream.get('title', '').split('\n', 1)[0],
                'hash': torrent_hash,
                'filename': behaviorhints.get('filename', ''),
                'size': source_utils.get_size(behaviorhints.get('videoSize', 0)),
                'byte_size': behaviorhints.get('videoSize', 0),
                'seeders': 0 if match_seeders is None else int(match_seeders.group(1)),
                'debrid_provider': debrid_provider,
                'source_provider': match_provider.group(1) if match_provider else 'Unknown',
                'cached': cached,
            })

        return list_

    @staticmethod
    def parse_torrentio_view(res, episode, cached=True):
        source = {
            'release_title': res['name'],
            'hash': res['hash'],
            'filename': res.get('filename', ''),
            'type': 'torrent',
            'quality': source_utils.getQuality(res['name']),
            'debrid_provider': res.get('debrid_provider'),
            'provider': 'torrentio',
            'episode_re': episode,
            'size': res['size'],
            'byte_size': res.get('byte_size', 0),
            'info': source_utils.getInfo(res['name']),
            'lang': source_utils.getAudio_lang(res['name']),
            'channel': source_utils.getAudio_channel(res['name']),
            'sub': source_utils.getSubtitle_lang(res['name']),
            'cached': cached,
            'seeders': res['seeders'],
        }

        if not cached:
            source['magnet'] = f"magnet:?xt=urn:btih:{res['hash']}"
            source['type'] += ' (uncached)'
            
        return source

    def append_cache_uncached_noduplicates(self):
        # Keep one source per (hash, debrid_provider) so multiple providers can show for the same torrent
        unique = {}
        for source in self.sources:
            key = (source.get('hash'), source.get('debrid_provider'))
            if not key[0]:
                continue
            if key in unique:
                current = unique[key]
                if source.get('seeders', -1) > current.get('seeders', -1):
                    unique[key] = source
                elif (source.get('seeders', -1) == current.get('seeders', -1)
                      and source.get('byte_size', 0) > current.get('byte_size', 0)):
                    unique[key] = source
            else:
                unique[key] = source

        self.cached = []
        self.uncached = []
        for source in unique.values():
            if source['cached']:
                self.cached.append(source)
            else:
                self.uncached.append(source)
