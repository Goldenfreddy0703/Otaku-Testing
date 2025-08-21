import json
import pickle
import re
import urllib.parse

from bs4 import BeautifulSoup, SoupStrainer
from resources.lib.ui import control, database
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.endpoints import malsync


class Sources(BrowserBase):
    _BASE_URL = 'https://hianime.sx/' if control.getBool('provider.hianimealt') else 'https://hianime.to/'
    _MEGA_URL = 'https://mega-embed-2.vercel.app/'

    def get_sources(self, mal_id, episode):
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        title = kodi_meta.get('name')
        title = self._clean_title(title)
        keyword = title

        all_results = []
        srcs = ['sub', 'dub', 'raw']
        if control.getInt('general.source') == 1:
            srcs.remove('dub')
        elif control.getInt('general.source') == 2:
            srcs.remove('sub')

        items = malsync.get_slugs(mal_id=mal_id, site='Zoro')
        if not items:
            if kodi_meta.get('start_date'):
                year = kodi_meta.get('start_date').split('-')[0]
                keyword += ' {0}'.format(year)

            headers = {'Referer': self._BASE_URL}
            params = {'keyword': keyword}
            res = database.get(
                self._get_request,
                8,
                self._BASE_URL + 'search',
                data=params,
                headers=headers
            )

            mlink = SoupStrainer('div', {'class': 'flw-item'})
            mdiv = BeautifulSoup(res, "html.parser", parse_only=mlink)
            sdivs = mdiv.find_all('h3')
            sitems = []
            for sdiv in sdivs:
                try:
                    slug = sdiv.find('a').get('href').split('?')[0]
                    stitle = sdiv.find('a').get('data-jname')
                    sitems.append({'title': stitle, 'slug': slug})
                except AttributeError:
                    pass

            if sitems:
                if title[-1].isdigit():
                    items = [x.get('slug') for x in sitems if title.lower() in x.get('title').lower()]
                else:
                    items = [x.get('slug') for x in sitems if (title.lower() + '  ') in (x.get('title').lower() + '  ')]
                if not items and ':' in title:
                    title = title.split(':')[0]
                    items = [x.get('slug') for x in sitems if (title.lower() + '  ') in (x.get('title').lower() + '  ')]

        if items:
            slug = items[0]
            all_results = self._process_aw(slug, title=title, episode=episode, langs=srcs)

        return all_results

    def _process_aw(self, slug, title, episode, langs):
        sources = []
        headers = {'Referer': self._BASE_URL}
        r = database.get(
            self._get_request,
            8,
            self._BASE_URL + 'ajax/v2/episode/list/' + slug.split('-')[-1],
            headers=headers,
            XHR=True
        )
        res = json.loads(r).get('html')
        elink = SoupStrainer('div', {'class': re.compile('^ss-list')})
        ediv = BeautifulSoup(res, "html.parser", parse_only=elink)
        items = ediv.find_all('a')
        e_id = [x.get('data-id') for x in items if int(x.get('data-number')) == int(episode)]
        if e_id:
            params = {'episodeId': e_id[0]}
            r = database.get(
                self._get_request,
                8,
                self._BASE_URL + 'ajax/v2/episode/servers',
                data=params,
                headers=headers,
                XHR=True
            )
            eres = json.loads(r).get('html')
            for lang in langs:
                elink = SoupStrainer('div', {'data-type': lang})
                sdiv = BeautifulSoup(eres, "html.parser", parse_only=elink)
                srcs = sdiv.find_all('div', {'class': 'item'})
                for src in srcs:
                    edata_id = src.get('data-id')
                    edata_name = src.text.strip().lower()
                    if edata_name.lower() in self.embeds():
                        params = {'id': edata_id}
                        r = self._get_request(
                            self._BASE_URL + 'ajax/v2/episode/sources',
                            data=params,
                            headers=headers,
                            XHR=True
                        )
                        slink = json.loads(r).get('link')
                        if edata_name == 'streamtape':
                            source = {
                                'release_title': '{0} - Ep {1}'.format(title, episode),
                                'hash': slink,
                                'type': 'embed',
                                'quality': 0,
                                'debrid_provider': '',
                                'provider': 'h!anime',
                                'size': 'NA',
                                'seeders': 0,
                                'byte_size': 0,
                                'info': [edata_name + (' DUB' if lang == 'dub' else ' SUB')],
                                'lang': 3 if lang == 'dub' else 2,
                                'channel': 3,
                                'sub': 1,
                                'skip': {}
                            }
                            sources.append(source)
                        else:
                            srclink = False
                            params = {'url': slink, 'referer': self._BASE_URL}

                            if control.getBool('ms_enable'):
                                ms_url = control.getSetting('ms_url')
                                mcs_url = urllib.parse.urljoin(ms_url, '/get')
                            else:
                                mcs_url = urllib.parse.urljoin(self._MEGA_URL, '/get')

                            try:
                                res = self._get_request(mcs_url, data=params)
                                res = json.loads(res)
                            except json.JSONDecodeError:
                                continue
                            subs = res.get('tracks')
                            if subs:
                                subs = [{'url': x.get('file'), 'lang': x.get('label')} for x in subs if x.get('kind') == 'captions']
                            skip = {}
                            if res.get('intro'):
                                skip['intro'] = res['intro']
                            if res.get('outro'):
                                skip['outro'] = res['outro']
                            if res.get('sources'):
                                srclink = res.get('sources')[0].get('file')
                            if not srclink:
                                continue
                            netloc = urllib.parse.urljoin(slink, '/')
                            headers = {'Referer': netloc, 'Origin': netloc[:-1]}
                            res = self._get_request(srclink, headers=headers)
                            quals = re.findall(r'#EXT.+?RESOLUTION=\d+x(\d+).*\n(?!#)(.+)', res)
                            if quals:
                                for qual, qlink in quals:
                                    qual = int(qual)
                                    if qual <= 480:
                                        quality = 1
                                    elif qual <= 720:
                                        quality = 2
                                    elif qual <= 1080:
                                        quality = 3
                                    else:
                                        quality = 0

                                    source = {
                                        'release_title': '{0} - Ep {1}'.format(title, episode),
                                        'hash': urllib.parse.urljoin(srclink, qlink) + '|User-Agent=iPad&{0}'.format(urllib.parse.urlencode(headers)),
                                        'type': 'direct',
                                        'quality': quality,
                                        'debrid_provider': '',
                                        'provider': 'h!anime',
                                        'size': 'NA',
                                        'seeders': 0,
                                        'byte_size': 0,
                                        'info': [edata_name + (' DUB' if lang == 'dub' else ' SUB')],
                                        'lang': 3 if lang == 'dub' else 2,
                                        'channel': 3,
                                        'sub': 1,
                                        'subs': subs,
                                        'skip': skip
                                    }
                                    sources.append(source)
                            else:
                                source = {
                                    'release_title': '{0} - Ep {1}'.format(title, episode),
                                    'hash': srclink + '|User-Agent=iPad&{0}'.format(urllib.parse.urlencode(headers)),
                                    'type': 'direct',
                                    'quality': 0,
                                    'debrid_provider': '',
                                    'provider': 'h!anime',
                                    'size': 'NA',
                                    'seeders': 0,
                                    'byte_size': 0,
                                    'info': [edata_name + (' DUB' if lang == 'dub' else ' SUB')],
                                    'lang': 3 if lang == 'dub' else 2,
                                    'channel': 3,
                                    'sub': 1,
                                    'subs': subs,
                                    'skip': skip
                                }
                                sources.append(source)

        return sources
