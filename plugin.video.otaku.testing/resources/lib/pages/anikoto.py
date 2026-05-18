# -*- coding: utf-8 -*-
import json
import pickle
import re
import urllib.parse

from bs4 import BeautifulSoup, SoupStrainer
from resources.lib.ui import control, database, embed_extractor, utils
from resources.lib.ui.BrowserBase import BrowserBase


class Sources(BrowserBase):
    """Embed source: anikototv.to. embed.config (cleaned): kiwistream, vibestream, vidcloud, vidstream, vidwish."""
    _BASE_URL = 'https://anikototv.to/'
    _MAPPER_API = 'https://mapper.mewcdn.online/api/mal/'
    _UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'

    _SERVER_GROUPS = frozenset({'sub', 'hsub', 'dub', 'adub'})

    def _ajax_headers(self, referer):
        referer = referer or self._BASE_URL
        origin = urllib.parse.urljoin(referer, '/').rstrip('/')
        return {
            'User-Agent': self._UA,
            'Referer': referer,
            'Origin': origin,
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/plain, */*',
        }

    def _matches_embed_allowlist(self, server_label):
        t = self.clean_embed_title(server_label)
        ek = frozenset(self.clean_embed_title(x) for x in self.embeds() if x)
        if not t or not ek:
            return False

        if 'kiwistream' in t:
            return 'kiwistream' in ek
        if 'vibestream' in t:
            return 'vibestream' in ek
        if 'vidcloud' in t:
            return 'vidcloud' in ek
        if 'vidstream' in t:
            return 'vidstream' in ek
        if 'vidwish' in t:
            return 'vidwish' in ek

        return False

    @staticmethod
    def _episode_stream_types():
        src_pref = control.getInt('general.source')
        allowed = {'sub', 'hsub', 'dub', 'adub'}
        if src_pref == 1:
            allowed.discard('dub')
            allowed.discard('adub')
        elif src_pref == 2:
            allowed -= {'sub', 'hsub'}
        return allowed

    @classmethod
    def _normalize_server_grp(cls, data_type_raw):
        s = (data_type_raw or '').strip().lower().replace('-', '').replace('_', '')
        return s if s in cls._SERVER_GROUPS else ''

    @staticmethod
    def _quality_from_stream_height(height_px):
        """Otaku tiers: 1 ≈ SD/≤480p, 2 ≈ ≤720p, 3 ≈ ≤1080p (same as playlist RESOLUTION logic)."""
        try:
            h = int(height_px)
        except (TypeError, ValueError):
            return 0
        if h <= 480:
            return 1
        if h <= 720:
            return 2
        if h <= 1080:
            return 3
        return 0

    @classmethod
    def _mapper_quality_hint_from_name(cls, raw_name):
        """Mapper JSON uses keys like Kiwi-Stream-720p; master playlist ladder may misrepresent rung."""
        m = re.match(r'^kiwi-stream-(\d{3,4})p$', (raw_name or '').strip().lower())
        if not m:
            return None
        q = cls._quality_from_stream_height(int(m.group(1)))
        return q or None

    def _search_candidates(self, keyword):
        headers = {'User-Agent': self._UA, 'Referer': self._BASE_URL}
        res = database.get(self._get_request, 8, urllib.parse.urljoin(self._BASE_URL, 'filter'),
                           data={'keyword': keyword}, headers=headers)
        if not res:
            return []
        soup = BeautifulSoup(res, 'html.parser', parse_only=SoupStrainer('div', {'id': 'list-items'}))
        out = []
        for item in soup.select('.item'):
            a = item.select_one('a.name.d-title')
            if not a:
                continue
            href = a.get('href') or ''
            m = re.search(r'/watch/([^/]+)/ep-(\d+)', href, re.I)
            if not m:
                continue
            out.append({
                'slug_part': m.group(1),
                'title_en': (a.text or '').strip(),
                'title_jp': (a.get('data-jp') or '').strip() or (a.text or '').strip(),
            })
        return out

    def _score_candidate(self, title, c):
        tl = title.lower().strip()
        tc = self.clean_embed_title(title)
        en_low = (c['title_en'] or '').lower() + '  '
        jp_low = (c['title_jp'] or '').lower()
        jc = self.clean_embed_title(c['title_jp'] or '')
        ec = self.clean_embed_title(c['title_en'] or '')

        if title.strip()[-1].isdigit():
            if tl + ' ' not in en_low and tl not in jp_low:
                return 0

        if tc == jc or tc == ec:
            return 100
        if tc:
            if tc in jc or jc in tc:
                return 90
            if tc in ec or ec in tc:
                return 85
            if jc and tc[:-1] == jc[:-1]:
                return 82
            if ec and tc[:-1] == ec[:-1]:
                return 82
        if tl + ' ' in en_low:
            return 72
        if tl and (tl in en_low or tl in jp_low):
            return 55
        return 0

    def _rank_candidates(self, title, cand):
        if not cand:
            return []
        scored = [(self._score_candidate(title, x), x) for x in cand]
        scored.sort(key=lambda x: x[0], reverse=True)
        ranked = []
        seen = set()
        for score, c in scored:
            if score <= 0:
                continue
            if c['slug_part'] in seen:
                continue
            seen.add(c['slug_part'])
            ranked.append(c)
        return ranked if ranked else cand

    def _watch_main_anime_id(self, html_page):
        m = re.search(r'id="watch-main"[^>]*\sdata-id="(\d+)"', html_page, re.I)
        return m.group(1) if m else None

    def _megaplayer_embed_to_direct(self, embed_url, title, episode, edata_name, lang_code, info_extra, ajax_skip=None):
        """Megaplayer template (Megaplay, Vidwish, …): embed page → #megaplay-player data-id → /stream/getSources."""
        embed_url = (embed_url or '').strip()
        purl = urllib.parse.urlparse(embed_url.split('?', 1)[0])
        if not purl.netloc:
            return []

        eh = {'User-Agent': self._UA, 'Referer': self._BASE_URL}
        emb = self._get_request(embed_url, headers=eh)
        if not emb:
            control.log(f'Anikoto: empty embed response {embed_url}', level='warning')
            return []

        pid = re.search(
            r'id="megaplay-player"[^>]*\sdata-id="(\d+)"',
            emb,
            re.I | re.S,
        )
        if not pid:
            control.log(f'Anikoto: megaplayer data-id missing for {embed_url}', level='warning')
            return []

        player_base = '{}://{}'.format(purl.scheme, purl.netloc)
        player_id = pid.group(1)
        gs_url = '{0}/stream/getSources?id={1}&id={1}'.format(player_base, player_id)
        gj = self._get_request(gs_url, headers={'User-Agent': self._UA, 'Referer': embed_url})

        skip = {}

        try:
            data = json.loads(gj or '{}')
        except json.JSONDecodeError:
            control.log('Anikoto: getSources invalid JSON', level='warning')
            return []

        src_obj = data.get('sources')
        srclink = None
        if isinstance(src_obj, dict):
            srclink = src_obj.get('file')
        elif isinstance(src_obj, list) and src_obj:
            srclink = src_obj[0].get('file')

        tracks = data.get('tracks')

        intro = data.get('intro')
        outro = data.get('outro')
        if isinstance(intro, dict):
            istart, iend = intro.get('start'), intro.get('end')
            if isinstance(istart, (int, float)) and isinstance(iend, (int, float)) and iend > istart:
                skip['intro'] = {'start': int(istart), 'end': int(iend)}
        if isinstance(outro, dict):
            ostart, oend = outro.get('start'), outro.get('end')
            if isinstance(ostart, (int, float)) and isinstance(oend, (int, float)) and oend > ostart:
                skip['outro'] = {'start': int(ostart), 'end': int(oend)}

        # Fallback: skip_data arrays from ajax/server (when getSources lacks ranges)
        if ajax_skip:
            intros = ajax_skip.get('intro')
            if isinstance(intros, list) and len(intros) == 2:
                start, end = intros[0], intros[1]
                try:
                    start, end = int(start), int(end)
                except (TypeError, ValueError):
                    start, end = 0, 0
                if end > start and 'intro' not in skip:
                    skip['intro'] = {'start': start, 'end': end}

            outros = ajax_skip.get('outro')
            if isinstance(outros, list) and len(outros) == 2:
                start, end = outros[0], outros[1]
                try:
                    start, end = int(start), int(end)
                except (TypeError, ValueError):
                    start, end = 0, 0
                if end > start:
                    skip['outro'] = {'start': start, 'end': end}

        if not srclink:
            control.log(f'Anikoto: no m3u8 in getSources for id={player_id}', level='warning')
            return []

        # CDNs expect Referer/Origin matching the player *site*, not deep embed paths (HAR: Referer vidwish.live/).
        origin = '{}://{}'.format(purl.scheme, purl.netloc)
        plist_hdr = {
            'User-Agent': self._UA,
            'Referer': '{}/'.format(origin),
            'Origin': origin,
        }
        if isinstance(tracks, list):
            subs = []
            for x in tracks:
                f = x.get('file')
                if not f:
                    continue
                kind = (x.get('kind') or '').lower()
                if kind and kind not in ('captions', 'subtitles'):
                    continue
                subs.append({
                    'url': f,
                    'lang': x.get('label') or '',
                    'headers': plist_hdr,
                })
        else:
            subs = []
        pl = self._get_request(srclink, headers=plist_hdr)
        if not pl:
            control.log(f'Anikoto: failed to fetch master playlist', level='warning')
            return []

        quality = 0
        quals = re.findall(r'#EXT.+?RESOLUTION=\d+x(\d+).*\n(?!#)(.+)', pl)
        if quals:
            qual_h = int(sorted(quals, key=lambda x: int(x[0]), reverse=True)[0][0])
            quality = self._quality_from_stream_height(qual_h)

        meta = ''.join((' ', info_extra)) if info_extra else ''
        source = {
            'release_title': '{0} - Ep {1}'.format(title, episode),
            'hash': srclink + '|User-Agent=iPad&{0}'.format(urllib.parse.urlencode(plist_hdr)),
            'type': 'direct',
            'quality': quality,
            'debrid_provider': '',
            'provider': 'anikoto',
            'size': 'NA',
            'seeders': 0,
            'byte_size': 0,
            'info': [edata_name + meta],
            'lang': lang_code,
            'channel': 3,
            'sub': 1,
            'subs': subs,
            'skip': skip,
        }
        return [source]

    def _kwik_embed_to_direct(
            self, embed_url, title, episode, edata_name, lang_code, info_extra,
            ajax_skip=None, quality_hint=None):
        """Kiwi (Kwik): embed resolves to vault/HLS URL in page JS (HAR: Referer kwik.cx/ → owocdn m3u8)."""
        h = {'User-Agent': self._UA, 'Referer': self._BASE_URL}
        html = self._get_request(embed_url, headers=h) or ''
        html = html + getattr(embed_extractor, '__get_packed_data')(html)
        m_src = re.search(r"const\s*source\s*=\s*'([^']+)", html)
        if not m_src:
            control.log(f'Anikoto: kwik embed missing const source ({embed_url})', level='warning')
            return []

        srclink = m_src.group(1)

        kwik_origin_url = '{}://{}'.format(*urllib.parse.urlparse(embed_url)[:2])
        plist_hdr = {
            'User-Agent': self._UA,
            'Referer': '{}/'.format(kwik_origin_url),
            'Origin': kwik_origin_url,
        }

        skip = {}
        if ajax_skip:
            intros = ajax_skip.get('intro')
            if isinstance(intros, list) and len(intros) == 2:
                start, end = intros[0], intros[1]
                try:
                    start, end = int(start), int(end)
                except (TypeError, ValueError):
                    start, end = 0, 0
                if end > start:
                    skip['intro'] = {'start': start, 'end': end}
            outros = ajax_skip.get('outro')
            if isinstance(outros, list) and len(outros) == 2:
                start, end = outros[0], outros[1]
                try:
                    start, end = int(start), int(end)
                except (TypeError, ValueError):
                    start, end = 0, 0
                if end > start:
                    skip['outro'] = {'start': start, 'end': end}

        pl = self._get_request(srclink, headers=plist_hdr)
        if not pl:
            control.log('Anikoto: failed to fetch kiwi playlist', level='warning')
            return []

        plist_quality = 0
        quals = re.findall(r'#EXT.+?RESOLUTION=\d+x(\d+).*\n(?!#)(.+)', pl)
        if quals:
            qual_h = int(sorted(quals, key=lambda x: int(x[0]), reverse=True)[0][0])
            plist_quality = self._quality_from_stream_height(qual_h)

        if quality_hint is not None:
            quality = quality_hint
        else:
            quality = plist_quality

        subs = []

        meta = ''.join((' ', info_extra)) if info_extra else ''
        source = {
            'release_title': '{0} - Ep {1}'.format(title, episode),
            'hash': srclink + '|User-Agent=iPad&{0}'.format(urllib.parse.urlencode(plist_hdr)),
            'type': 'direct',
            'quality': quality,
            'debrid_provider': '',
            'provider': 'anikoto',
            'size': 'NA',
            'seeders': 0,
            'byte_size': 0,
            'info': [edata_name + meta],
            'lang': lang_code,
            'channel': 3,
            'sub': 1,
            'subs': subs,
            'skip': skip,
        }
        return [source]

    def _ajax_embed_url_to_direct(
            self, embed_url, title, episode, edata_name, lang_code, info_extra,
            ajax_skip, mapper_quality_hint=None):
        host = urllib.parse.urlsplit(embed_url).netloc.lower()
        if 'kwik.' in host:
            return self._kwik_embed_to_direct(
                embed_url, title, episode, edata_name, lang_code, info_extra.strip(), ajax_skip,
                quality_hint=mapper_quality_hint)
        # Megaplay / Vidwish / same player stack
        return self._megaplayer_embed_to_direct(
            embed_url, title, episode, edata_name, lang_code, info_extra.strip(), ajax_skip)

    def _resolve_one_server(self, args):
        """Args: link_id, name, grp, title, episode, watch_url."""
        link_id = args['link_id']
        name = args['name']
        grp = args['grp']
        title = args['title']
        episode = args['episode']
        watch_url = args['watch_url']

        h = self._ajax_headers(watch_url)
        rtxt = self._get_request(
            urllib.parse.urljoin(self._BASE_URL, 'ajax/server'),
            data={'get': link_id},
            headers=h,
        )
        try:
            j = json.loads(rtxt or '{}')
        except json.JSONDecodeError:
            control.log(f'Anikoto: ajax/server decode failed ({name})', level='warning')
            return []

        res = j.get('result')
        if not isinstance(res, dict):
            control.log(f'Anikoto: ajax/server unexpected payload ({name})', level='warning')
            return []

        url = res.get('url')
        ajax_skip = res.get('skip_data')
        if not url:
            return []

        if grp == 'dub':
            lang_code = 3
            info_extra = ' DUB'
        elif grp == 'adub':
            lang_code = 3
            info_extra = ' A-DUB'
        elif grp == 'hsub':
            lang_code = 2
            info_extra = ' HSUB'
        else:
            lang_code = 2
            info_extra = ' SUB'

        q_hint = self._mapper_quality_hint_from_name(name)
        return self._ajax_embed_url_to_direct(
            url, title, episode, self._source_info_label(name), lang_code, info_extra.strip(), ajax_skip,
            mapper_quality_hint=q_hint)

    @staticmethod
    def _source_info_label(name):
        """Short list label: Kiwi mapper uses Kiwi-Stream-720p keys; hide resolution here (shown on stream row)."""
        s = (name or '').strip().lower()
        if s == 'kiwi-stream' or s.startswith('kiwi-stream-'):
            return 'kiwi-stream'
        return s

    @staticmethod
    def _capitalize_first(s):
        s = s or ''
        return s[0].upper() + s[1:] if s else s

    @classmethod
    def _mapper_row_label(cls, provider_key):
        """Match anikoto `mapper.js` naming (gogoanime→Vidstream, anivibe→vibe-Stream, animepahe→Kiwi-Stream)."""
        k = provider_key or ''
        if k == 'gogoanime':
            t = 'Vidstream'
        elif k == 'anivibe':
            t = 'vibe-Stream'
        elif k == 'animepahe':
            t = 'Kiwi-Stream'
        else:
            t = k
        return cls._capitalize_first(t)

    def _servers_from_mapper_api(self, mal, slug, timestamp, allowed_grp):
        """H-SUB / A-DUB Kiwi (and extra mirrors) come from mewcdn mapper, not ajax/server/list."""
        if mal in (None, '') or slug in (None, '') or timestamp in (None, ''):
            return []
        mp_url = ''.join((self._MAPPER_API, str(mal), '/', str(slug), '/', str(timestamp)))
        mh = {'User-Agent': self._UA, 'Referer': self._BASE_URL, 'Accept': 'application/json, text/plain, */*'}
        raw = database.get(self._get_request, 8, mp_url, headers=mh)
        try:
            data = json.loads(raw or '{}')
        except json.JSONDecodeError:
            control.log('Anikoto: mapper API JSON decode failed', level='warning')
            return []
        if not isinstance(data, dict):
            return []

        data.pop('status', None)
        queue = []
        seen = set()

        for key, blob in data.items():
            if not isinstance(blob, dict):
                continue
            name = self._mapper_row_label(key)

            side = blob.get('sub')
            if isinstance(side, dict) and 'hsub' in allowed_grp:
                lid = side.get('url')
                lid = lid.strip() if isinstance(lid, str) else ''
                if lid and lid not in seen and self._matches_embed_allowlist(name.lower()):
                    seen.add(lid)
                    queue.append({'link_id': lid, 'name': name.lower(), 'grp': 'hsub'})

            side = blob.get('dub')
            if isinstance(side, dict) and 'adub' in allowed_grp:
                lid = side.get('url')
                lid = lid.strip() if isinstance(lid, str) else ''
                if lid and lid not in seen and self._matches_embed_allowlist(name.lower()):
                    seen.add(lid)
                    queue.append({'link_id': lid, 'name': name.lower(), 'grp': 'adub'})

        return queue

    def _servers_from_html(self, html_fragment, allowed_grp):
        st = BeautifulSoup(html_fragment or '', 'html.parser')
        queue = []
        seen = set()
        for bloc in st.select('.servers > .type'):
            raw_type = bloc.get('data-type')
            # After mapper.js runs, duplicate blocks keep data-type=sub|dub but labels read H-SUB / A-DUB.
            lbl_el = bloc.find('label')
            label_txt = ((lbl_el.get_text() if lbl_el else '') or '').upper()
            if 'H-SUB' in label_txt or 'HSUB' in label_txt.replace(' ', ''):
                dt_norm = 'hsub'
            elif 'A-DUB' in label_txt or 'ADUB' in label_txt.replace(' ', ''):
                dt_norm = 'adub'
            else:
                dt_norm = self._normalize_server_grp(raw_type)

            if not dt_norm or dt_norm not in allowed_grp:
                continue
            for li in bloc.select('li[data-link-id]'):
                label = li.get_text(strip=True)
                lid = li.get('data-link-id')
                if not lid or lid in seen:
                    continue
                if not self._matches_embed_allowlist(label):
                    continue
                seen.add(lid)
                queue.append({'link_id': lid, 'name': label, 'grp': dt_norm})
        return queue

    def _try_slug(self, slug_part, mal_id, episode, title):
        episode = int(episode)
        watch_url = urllib.parse.urljoin(self._BASE_URL, 'watch/%s/ep-%s' % (slug_part, episode))

        wm = database.get(self._get_request, 8, watch_url, headers={
            'User-Agent': self._UA,
            'Referer': self._BASE_URL,
        })
        if not wm:
            return []

        anime_nid = self._watch_main_anime_id(wm)
        if not anime_nid:
            control.log(f'Anikoto: missing watch-main id for slug {slug_part}', level='warning')
            return []

        ep_endpoint = urllib.parse.urljoin(self._BASE_URL, 'ajax/episode/list/' + anime_nid)
        ep_raw = database.get(self._post_request, 8, ep_endpoint, data={
            'style': '',
            'vrf': '1',
        }, headers=self._ajax_headers(watch_url))
        try:
            ep_doc = json.loads(ep_raw or '{}')
        except json.JSONDecodeError:
            control.log('Anikoto: episode/list JSON decode failed', level='warning')
            return []

        ep_html = ep_doc.get('result', '')
        if not ep_html:
            return []

        allowed_grp = self._episode_stream_types()

        data_ids = None
        anchor_mal = anchor_slug = anchor_ts = None
        ep_soup = BeautifulSoup(ep_html, 'html.parser', parse_only=SoupStrainer('a'))
        for anchor in ep_soup.find_all('a', attrs={'data-num': True}):
            try:
                if int(anchor.get('data-num')) != episode:
                    continue
            except (TypeError, ValueError):
                continue
            smal = anchor.get('data-mal')
            if smal not in (None, ''):
                try:
                    if int(str(smal)) != int(str(mal_id)):
                        control.log(
                            'Anikoto: MAL mismatch on slug %s episode %s (expected %s, got %s)' % (
                                slug_part, episode, mal_id, smal),
                            level='notice',
                        )
                        return []
                except (TypeError, ValueError):
                    pass

            data_ids = anchor.get('data-ids')
            anchor_mal = anchor.get('data-mal')
            anchor_slug = anchor.get('data-slug')
            anchor_ts = anchor.get('data-timestamp')
            break

        if not data_ids:
            control.log(f'Anikoto: episode {episode} not in list ({slug_part})', level='warning')
            return []

        sl_raw = database.get(self._get_request, 8,
                              urllib.parse.urljoin(self._BASE_URL, 'ajax/server/list'),
                              data={'servers': data_ids}, headers=self._ajax_headers(watch_url))
        try:
            sj = json.loads(sl_raw or '{}')
        except json.JSONDecodeError:
            control.log('Anikoto: server/list JSON decode failed', level='warning')
            return []

        server_html = sj.get('result', '')
        srv_queue = self._servers_from_html(server_html, allowed_grp)

        mapper_q = self._servers_from_mapper_api(anchor_mal, anchor_slug, anchor_ts, allowed_grp)

        seen_ids = set()
        merged = []
        for row in srv_queue + mapper_q:
            lid = row.get('link_id')
            if not lid or lid in seen_ids:
                continue
            seen_ids.add(lid)
            merged.append(row)

        if not merged:
            control.log(f'Anikoto: no allowed servers/embeds ({slug_part} ep {episode})', level='notice')
            return []

        build_arg = [{'link_id': s['link_id'], 'name': s['name'], 'grp': s['grp'],
                      'title': title, 'episode': episode, 'watch_url': watch_url} for s in merged]
        buckets = utils.parallel_process(build_arg, self._resolve_one_server)
        out = []
        for b in buckets:
            out.extend(b or [])
        return out

    def get_sources(self, mal_id, episode):
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        raw_title = kodi_meta.get('name')
        title = self._clean_title(raw_title)
        year = None
        if kodi_meta.get('start_date'):
            year = kodi_meta['start_date'].split('-')[0]
            cand = self._search_candidates('{0} {1}'.format(title, year))
            if not cand:
                cand = self._search_candidates(title)
        else:
            cand = self._search_candidates(title)
        ranked = self._rank_candidates(title, cand)
        control.log(f'Anikoto: {len(ranked)} search candidate(s) for "{title}"', level='info')

        for c in ranked:
            src = self._try_slug(c['slug_part'], mal_id, episode, title)
            if src:
                return src

        control.log(f'Anikoto: no streams for "{title}" MAL={mal_id} ep={episode}', level='notice')
        return []
