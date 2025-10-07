import json

from bs4 import BeautifulSoup, SoupStrainer
from resources.lib.ui import database, source_utils, control
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.endpoints import malsync


class Sources(BrowserBase):
    _BASE_URL = 'https://animepahe.si/'
    _headers = {
        'Referer': _BASE_URL,
        'Cookie': '__ddg1_=PZYJSmACHBBQGP6auJU9; __ddg2_=hxAe1bBqtlUhMFik'
    }

    def get_sources(self, mal_id, episode):
        title = malsync.get_title(mal_id, site='animepahe')
        if not title:
            return []
        params = {'m': 'search', 'q': title}
        r = database.get(
            self._get_request,
            8,
            self._BASE_URL + 'api',
            data=params,
            headers=self._headers
        )
        try:
            sitems = json.loads(r).get('data')
        except json.JSONDecodeError:
            return []

        if not sitems and ':' in title:
            title = title.split(':')[0]
            params.update({'q': title})
            r = database.get(
                self._get_request,
                8,
                self._BASE_URL + 'api',
                data=params,
                headers=self._headers
            )
            sitems = json.loads(r).get('data')

        all_results = []
        if sitems:
            if title[-1].isdigit():
                items = [x for x in sitems if title.lower() in x.get('title').lower()]
            else:
                items = [x for x in sitems if (title.lower() + '  ') in (x.get('title').lower() + '  ')]
            if not items:
                items = sitems
            if items:
                slug = items[0].get('session')
                all_results = self._process_ap(slug, title=title, episode=episode)
        return all_results

    def _process_ap(self, slug, title, episode):
        sources = []
        e_num = int(episode)
        big_series = e_num > 30
        page = 1
        if big_series:
            page += int(e_num / 30)

        params = {
            'm': 'release',
            'id': slug,
            'sort': 'episode_asc',
            'page': page
        }
        r = database.get(
            self._get_request,
            8,
            self._BASE_URL + 'api',
            data=params,
            headers=self._headers
        )
        r = json.loads(r)
        items = r.get('data')
        items = sorted(items, key=lambda x: x.get('episode'))

        if items[0].get('episode') > 1 and not big_series:
            e_num = e_num + items[0].get('episode') - 1

        items = [x for x in items if x.get('episode') == e_num]
        if items:
            eurl = self._BASE_URL + 'play/' + slug + '/' + items[0].get('session')
            html = self._get_request(eurl, headers=self._headers)
            mlink = SoupStrainer('div', {'id': 'resolutionMenu'})
            mdiv = BeautifulSoup(html, "html.parser", parse_only=mlink)
            items = mdiv.find_all('button')

            # Track which language we've found sources for
            sources_found_per_lang = {}
            control.log(f"AnimePahe: Found {len(items)} quality options")

            for item in items:
                if any(x in item.get('data-src').lower() for x in self.embeds()):
                    lang = 3 if item.get('data-audio') == 'eng' else 2

                    # Skip if we already have a source for this language
                    if lang in sources_found_per_lang:
                        control.log(f"AnimePahe: Skipping duplicate language {lang}")
                        continue

                    qual = int(item.get('data-resolution'))
                    if qual <= 577:
                        quality = 1
                    elif qual <= 721:
                        quality = 2
                    elif qual <= 1081:
                        quality = 3
                    else:
                        quality = 0

                    source = {
                        'release_title': '{0} - Ep {1}'.format(title, episode),
                        'hash': item.get('data-src'),
                        'type': 'embed',
                        'quality': quality,
                        'debrid_provider': '',
                        'provider': 'animepahe',
                        'size': 'NA',
                        'seeders': 0,
                        'byte_size': 0,
                        'info': [source_utils.get_embedhost(item.get('data-src')) + (' DUB' if item.get('data-audio') == 'eng' else ' SUB')],
                        'lang': lang,
                        'channel': 3,
                        'sub': 1
                    }
                    sources.append(source)
                    sources_found_per_lang[lang] = True
                    control.log(f"AnimePahe: Found source for lang {lang}, quality {quality}")

        return sources
