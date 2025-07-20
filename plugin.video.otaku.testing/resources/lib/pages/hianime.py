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
    _KEY_URL = 'https://megacloud.blog/js/player/a/v2/pro/embed-1.min.js?v={0}'
    _DECODE_URL = "https://script.google.com/macros/s/AKfycbx-yHTwupis_JD0lNzoOnxYcEYeXmJZrg7JeMxYnEZnLBy5V0--UxEvP-y9txHyy1TX9Q/exec"

    def get_sources(self, mal_id, episode):
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        title = kodi_meta.get('name')
        title = self._clean_title(title)
        keyword = title

        all_results = []
        srcs = ['sub', 'dub', 'raw']
        if control.getSetting('general.source') == 'Sub':
            srcs.remove('dub')
        elif control.getSetting('general.source') == 'Dub':
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
                            headers = {'Referer': self._BASE_URL}
                            resp = self._get_request(slink, headers=headers)
                            r = re.search(r'\b([a-zA-Z0-9]{48})\b', resp)
                            if r:
                                nonce = r.group(1)
                                headers = {'Referer': slink}
                                sl = urllib.parse.urlparse(slink)
                                spath = sl.path.split('/')
                                sid = spath.pop(-1)
                                eurl = '{}://{}{}/getSources'.format(sl.scheme, sl.netloc, '/'.join(spath))
                                params = {
                                    'id': sid,
                                    '_k': nonce
                                }
                                res = self._get_request(
                                    eurl,
                                    data=params,
                                    headers=headers,
                                    XHR=True
                                )
                                res = json.loads(res)
                                subs = res.get('tracks')
                                if subs:
                                    subs = [{'url': x.get('file'), 'lang': x.get('label')} for x in subs if x.get('kind') == 'captions']
                                skip = {}
                                if res.get('intro'):
                                    skip['intro'] = res['intro']
                                if res.get('outro'):
                                    skip['outro'] = res['outro']
                                if res.get('encrypted'):
                                    srclink = self._process_link(res.get('sources'), nonce)
                                elif res.get('sources'):
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

    def _process_link(self, sources, nonce):
        # Thanks to yogesh-hacker
        secret = database.get(self.mega_secret, 1)
        if secret:
            params = {
                'encrypted_data': sources,
                'nonce': nonce,
                'secret': secret
            }
            result = self._get_request(self._DECODE_URL, data=params)
            r = re.search(r'"file":"([^"]+)', result)
            if r:
                return r.group(1)
        return ''

    def mega_secret(self):
        # Thanks to yogesh-hacker
        api_url = 'https://api.github.com/repos/'
        repo_path = 'yogesh-hacker/MegacloudKeys/'
        data_url = 'https://raw.githubusercontent.com/'
        commits = 'commits?path='
        file_path = '/keys.json'
        r = json.loads(self._get_request(api_url + repo_path + commits + file_path[1:] + '&per_page=3'))
        cid = r[0].get('sha')
        res = json.loads(self._get_request(data_url + repo_path + cid + file_path))
        return res.get('mega')
