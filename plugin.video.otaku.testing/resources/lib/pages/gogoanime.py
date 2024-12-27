import itertools
import json
import pickle
import re

from functools import partial
from bs4 import BeautifulSoup
from resources.lib.ui import control, client, database, source_utils
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.indexers import malsync


def get_backup(mal_id, source):
    params = {
        "type": "myanimelist",
        "id": mal_id
    }
    r = client.request("https://arm2.vercel.app/api/kaito-b", params=params)
    return json.loads(r.content).get('Pages', {}).get(source, {}) if r.ok else {}


class Sources(BrowserBase):
    _BASE_URL = 'https://anitaku.to/' if control.getBool('provider.gogoalt') else 'https://gogoanime3.cc/'

    def get_sources(self, mal_id, episode):
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        title = kodi_meta.get('name')
        title = self._clean_title(title)

        slugs = malsync.get_slugs(mal_id=mal_id, site='Gogoanime')
        if not slugs:
            headers = {'Referer': self._BASE_URL}
            params = {
                'keyword': title,
                'id': -1,
                'link_web': self._BASE_URL
            }
            r = database.get(
                self._get_request,
                8,
                'https://ajax.gogo-load.com/site/loadAjaxSearch',
                data=params,
                headers=headers
            )
            r = json.loads(r).get('content')

            if not r and ':' in title:
                title = title.split(':')[0]
                params.update({'keyword': title})
                r = database.get(
                    self._get_request,
                    8,
                    'https://ajax.gogo-load.com/site/loadAjaxSearch',
                    data=params,
                    headers=headers
                )
                r = json.loads(r).get('content')

            soup = BeautifulSoup(r, 'html.parser')
            items = soup.find_all('div', {'class': 'list_search_ajax'})
            if len(items) == 1:
                slugs = [items[0].find('a').get('href').split('/')[-1]]
            else:
                slugs = [
                    item.find('a').get('href').split('/')[-1]
                    for item in items
                    if ((item.a.text.strip() + '  ').lower()).startswith((title + '  ').lower())
                    or ((item.a.text.strip() + '  ').lower()).startswith((title + ' (Dub)  ').lower())
                    or ((item.a.text.strip() + '  ').lower()).startswith((title + ' (TV)  ').lower())
                    or ((item.a.text.strip() + '  ').lower()).startswith((title + ' (TV) (Dub)  ').lower())
                    or ((item.a.text.strip().replace(' - ', ' ') + '  ').lower()).startswith((title + '  ').lower())
                    or (item.a.text.strip().replace(':', ' ') + '   ').startswith(title + '   ')
                ]
            if not slugs:
                slugs = database.get(get_backup, 168, mal_id, 'Gogoanime')
                if not slugs:
                    return []
        slugs = list(slugs.keys()) if isinstance(slugs, dict) else slugs
        mapfunc = partial(self._process_gogo, show_id=mal_id, episode=episode)
        all_results = list(map(mapfunc, slugs))
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _process_gogo(self, slug, show_id, episode):
        if slug.startswith('http'):
            slug = slug.split('/')[-1]
        url = "{0}{1}-episode-{2}".format(self._BASE_URL, slug, episode)
        headers = {'Referer': self._BASE_URL}
        title = (slug.replace('-', ' ')).title() + ' - Ep {0}'.format(episode)
        r = database.get(
            self._send_request,
            8,
            url,
            headers=headers
        )

        if not r:
            url = '{0}category/{1}'.format(self._BASE_URL, slug)
            html = database.get(
                self._send_request,
                8,
                url,
                headers=headers
            )
            mid = re.findall(r'value="([^"]+)"\s*id="movie_id"', html)
            if mid:
                params = {'ep_start': episode,
                          'ep_end': episode,
                          'id': mid[0],
                          'alias': slug}
                eurl = 'https://ajax.gogo-load.com/ajax/load-list-episode'
                r2 = self._get_request(eurl, data=params, headers=headers)
                soup2 = BeautifulSoup(r2, 'html.parser')
                eslug = soup2.find('a')
                if eslug:
                    eslug = eslug.get('href').strip()
                    url = "{0}{1}".format(self._BASE_URL[:-1], eslug)
                    r = self._send_request(url, headers=headers)

        soup = BeautifulSoup(r, 'html.parser')
        sources = []
        for element in soup.select('.anime_muti_link > ul > li'):
            server = element.get('class')[0]
            link = element.a.get('data-video')

            if server.lower() in self.embeds():
                if link.startswith('//'):
                    link = 'https:' + link

                # Check if the slug ends with '-dub' or '-sub', if not, append '-sub'
                if not slug.endswith('-dub') and not slug.endswith('-sub'):
                    slug += '-sub'

                source = {
                    'release_title': title,
                    'hash': link,
                    'type': 'embed',
                    'quality': 0,
                    'debrid_provider': '',
                    'provider': 'gogo',
                    'size': 'NA',
                    'byte_size': 0,
                    'info': source_utils.getInfo(slug) + [server],
                    'lang': source_utils.getAudio_lang(title),
                    'channel': source_utils.getAudio_channel(title),
                    'sub': source_utils.getSubtitle_lang(title),
                }
                sources.append(source)

        return sources
