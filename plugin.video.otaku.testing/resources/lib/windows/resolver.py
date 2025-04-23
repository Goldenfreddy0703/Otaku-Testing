import xbmcgui
import xbmcplugin
import xbmc
import urllib.parse

from resources.lib.WatchlistIntegration import watchlist_update_episode
from resources.lib.debrid import all_debrid, debrid_link, premiumize, real_debrid, torbox, easydebrid
from resources.lib.ui import client, control, source_utils, player
from resources.lib.windows.base_window import BaseWindow

control.sys.path.append(control.dataPath)


class hook_mimetype:
    __MIME_HOOKS = {}

    @classmethod
    def trigger(cls, mimetype, item):
        if mimetype in cls.__MIME_HOOKS.keys():
            return cls.__MIME_HOOKS[mimetype](item)
        return item

    def __init__(self, mimetype):
        self._type = mimetype

    def __call__(self, func):
        assert self._type not in self.__MIME_HOOKS.keys()
        self.__MIME_HOOKS[self._type] = func
        return func


class Resolver(BaseWindow):
    def __init__(self, xml_file, location, actionArgs=None, source_select=False):
        super().__init__(xml_file, location, actionArgs=actionArgs)
        self.return_data = {
            'link': None,
            'linkinfo': None,
            'source': None
        }
        self.canceled = False
        self.sources = None
        self.args = None
        self.resolvers = {
            'Alldebrid': all_debrid.AllDebrid,
            'Debrid-Link': debrid_link.DebridLink,
            'Premiumize': premiumize.Premiumize,
            'Real-Debrid': real_debrid.RealDebrid,
            'TorBox': torbox.TorBox,
            'EasyDebrid': easydebrid.EasyDebrid
        }
        self.source_select = source_select
        self.pack_select = False
        self.mal_id = actionArgs['mal_id']
        # self.season = database.get_episode(self.mal_id)['season']
        self.episode = int(actionArgs.get('episode', 1))
        self.play = actionArgs.get('play')
        self.source_select_close = actionArgs.get('close')
        self.resume = actionArgs.get('resume')
        self.context = actionArgs.get('context')
        self.silent = actionArgs.get('silent')
        self.params = actionArgs.get('params', {})
        self.autoruninbackground = control.getBool('uncached.autoruninbackground')
        self.autoruninforground = control.getBool('uncached.autoruninforground')
        self.autoskipuncached = control.getBool('uncached.autoskipuncached')
        self.abort = False

        # if self.season:
        #     control.setStr('resolve_season', str(self.season))

        if self.source_select:
            control.setSetting('last_played_source', None)

    def onInit(self):
        self.sources = self.reorder_sources(self.sources)
        self.resolve(self.sources)

    def reorder_sources(self, sources):
        # last played source move to top of list
        if len(sources) > 1 and not self.source_select:
            last_played = control.getSetting('last_played_source')
            episode_value = str(self.episode)
            episode_value_length = len(episode_value)  # Get the length of episode_value
            for index, source in enumerate(sources):
                if source['type'] in ['embed', 'direct']:
                    concatenated_info = str(source['provider']) + " ".join(map(str, source['info']))
                    if concatenated_info == last_played:
                        sources.insert(0, sources.pop(index))
                        break
                elif source['type'] in ['torrent', 'torrent (uncached)', 'cloud', 'hoster', 'local']:
                    release_title = str(source['release_title'])
                    chars = list(last_played)
                    match_found = False

                    i = 0
                    while i < len(chars):
                        if chars[i].isdigit():
                            # Check if there's enough room to replace episode_value_length digits
                            if i + episode_value_length <= len(chars) and all(c.isdigit() for c in chars[i:i + episode_value_length]):
                                # Replace the next episode_value_length digits with episode_value
                                for j in range(episode_value_length):
                                    chars[i + j] = episode_value[j]
                                modified_last_played = ''.join(chars)

                                if modified_last_played == release_title:
                                    sources.insert(0, sources.pop(index))
                                    match_found = True
                                    break  # Found a match, no need to continue

                                # Reset the modified characters if not a match
                                for j in range(episode_value_length):
                                    chars[i + j] = last_played[i + j]

                            i += episode_value_length  # Move past the digits just checked or replaced
                        else:
                            i += 1  # Move to the next character if the current one is not a digit

                        if match_found:
                            break

                        if not match_found:
                            if str(source['release_title']) == last_played:
                                sources.insert(0, sources.pop(index))
                                break
        return sources

    def resolve(self, sources):
        for i in sources:
            self.return_data['source'] = i
            if self.canceled:
                break
            debrid_provider = i.get('debrid_provider', 'None').replace('_', ' ')
            self.setProperty('debrid_provider', debrid_provider)
            self.setProperty('source_provider', i['provider'])
            self.setProperty('release_title', str(i['release_title']))
            self.setProperty('source_resolution', source_utils.res[i['quality']])
            self.setProperty('source_info', " ".join(i['info']))
            self.setProperty('source_type', i['type'])

            if 'uncached' in i['type']:
                if not self.autoskipuncached:
                    self.return_data['link'] = self.resolve_uncache(i)
                else:
                    stream_link = self.resolve_uncache(i)
                    if stream_link:
                        self.return_data['link'] = stream_link
                        break

            if i['type'] in ['torrent', 'cloud', 'hoster']:
                if i['type'] == 'cloud' and i['debrid_provider'] == 'Alldebrid':
                    stream_link = i['hash']
                else:
                    stream_link = self.resolve_source(self.resolvers[i['debrid_provider']], i)
                if stream_link:
                    self.return_data['link'] = stream_link
                    break

            elif i['type'] == 'direct':
                stream_link = i['hash']
                if stream_link:
                    self.return_data['link'] = stream_link
                    if i.get('subs'):
                        self.return_data['link'] = stream_link
                        self.return_data['sub'] = i['subs']
                    break

            elif i['type'] == 'embed':
                from resources.lib.ui import embed_extractor
                stream_link = embed_extractor.load_video_from_url(i['hash'])
                if stream_link:
                    self.return_data['link'] = stream_link
                    break

            elif i['type'] == 'local':
                stream_link = i['hash']
                self.return_data = {
                    'url': stream_link,
                    'local': True,
                    'headers': {}
                }
                break

        if self.return_data.get('local'):
            self.return_data['linkinfo'] = self.return_data
        else:
            self.return_data['linkinfo'] = self.prefetch_play_link(self.return_data['link'])

        if not self.return_data['linkinfo']:
            self.return_data = False
        if self.play and isinstance(self.return_data, dict):
            if self.source_select_close:
                self.source_select_close()
            linkInfo = self.return_data['linkinfo']
            item = xbmcgui.ListItem(path=linkInfo['url'], offscreen=True)
            if self.return_data.get('sub'):
                from resources.lib.ui import embed_extractor
                embed_extractor.del_subs()
                subtitles = []
                for sub in self.return_data['sub']:
                    sub_url = sub.get('url')
                    sub_lang = sub.get('lang')
                    subtitles.append(embed_extractor.get_sub(sub_url, sub_lang))
                item.setSubtitles(subtitles)

            if linkInfo['headers'].get('Content-Type'):
                item.setProperty('MimeType', linkInfo['headers']['Content-Type'])
                # Run any mimetype hook
                item = hook_mimetype.trigger(linkInfo['headers']['Content-Type'], item)

            if self.context:
                control.set_videotags(item, self.params)
                art = {
                    'icon': self.params.get('icon'),
                    'thumb': self.params.get('thumb'),
                    'fanart': self.params.get('fanart'),
                    'landscape': self.params.get('landscape'),
                    'banner': self.params.get('banner'),
                    'clearart': self.params.get('clearart'),
                    'clearlogo': self.params.get('clearlogo'),
                    'tvshow.poster': self.params.get('tvshow.poster')
                }
                item.setArt(art)
                control.playList.add(linkInfo['url'], item)
                xbmc.Player().play(control.playList, item)
            else:
                xbmcplugin.setResolvedUrl(control.HANDLE, True, item)
            monitor = Monitor()
            for _ in range(30):
                if monitor.waitForAbort(1) or monitor.playbackerror or monitor.abortRequested():
                    xbmcplugin.setResolvedUrl(control.HANDLE, False, item)
                    control.playList.clear()
                    self.abort = True
                    break
                if monitor.playing:
                    break
            else:
                control.log('no xbmc playing source found; Continuing code', 'warning')
            del monitor
            self.close()
            if not self.abort:
                player.WatchlistPlayer().handle_player(
                    self.mal_id,
                    watchlist_update_episode,
                    self.episode,
                    self.resume,
                    self.params.get('path', ''),
                    self.return_data['source']['type'] if 'type' in self.return_data['source'] else '',
                    self.return_data['source']['provider'] if 'provider' in self.return_data['source'] else '',
                    self.context
                )
        else:
            self.close()

    def resolve_source(self, api, source):
        api = api()
        hash_ = source['hash']
        magnet = f"magnet:?xt=urn:btih:{hash_}"
        stream_link = {}
        if source['type'] == 'torrent':
            stream_link = api.resolve_single_magnet(hash_, magnet, source['episode_re'], self.pack_select)
        elif source['type'] == 'cloud':
            hash_ = api.resolve_cloud(source, self.pack_select)
            if hash_:
                stream_link = api.resolve_hoster(hash_)
        elif source['type'] == 'hoster':
            # Get the hoster links from EasyDebrid.
            hoster_response = api.resolve_hoster(magnet, source['episode_re'], self.pack_select)
            if hoster_response:
                stream_link = hoster_response
        return stream_link

    @staticmethod
    def prefetch_play_link(link):
        if not link:
            return
        url = link
        headers = {}
        if '|' in url:
            url, hdrs = url.split('|')
            headers = dict([item.split('=') for item in hdrs.split('&')])
            for header in headers:
                headers[header] = urllib.parse.unquote_plus(headers[header])

        # If flaresolverr is enabled, fetch cookies to bypass Cloudflare
        if control.getBool('fs_enable'):
            from resources.lib.ui.client import cfcookie
            cookie_obj = cfcookie()
            cookie, ua = cookie_obj.get(url, control.getInt('fs_timeout'))
            if cookie:
                headers["Cookie"] = cookie
                headers["User-Agent"] = ua

        limit = None if '.m3u8' in url else '0'
        linkInfo = client.request(url, headers=headers, limit=limit, output='extended', error=True)
        if linkInfo[1] not in ['200', '201']:
            raise Exception('could not resolve %s. status_code=%s' %
                            (link, linkInfo[1]))
        return {
            "url": link if '|' in link else linkInfo[5],
            "headers": linkInfo[2],
        }

    def resolve_uncache(self, source):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        status = None
        api = self.resolvers[source['debrid_provider']]()
        f_string = (f"[I]{source['release_title']}[/I][CR]"
                    f"[CR]"
                    f"This source is not cached. Would you like to cache it now?")

        if source['debrid_provider'] == 'Debrid-Link':
            control.ok_dialog(heading, 'Cache Resolver has not been added for Debrid-Link')
            return

        if source['debrid_provider'] in ['Alldebrid', 'Real-Debrid']:
            # Get an instance of the debrid API and check torrent status early.
            torrent_status = api.get_torrent_status(source['magnet'])
            # torrent_status returns (torrent_id, status, torrent_info)
            if torrent_status is None or torrent_status[0] is None:
                # Torrent selection failed.
                return

            torrent_id, status, torrent_info = torrent_status
            if source['debrid_provider'] == 'Alldebrid':
                api.delete_magnet(torrent_id)
            else:
                api.deleteTorrent(torrent_id)

        # If the file is already cached, bypass any prompting.
        if status in ['downloaded', 'Ready']:
            runbackground = False
            runinforground = False
        else:
            # Not yet cached: decide based on settings or prompt the user.
            if self.autoruninbackground:
                runbackground = True
                runinforground = False
            elif self.autoruninforground:
                runbackground = False
                runinforground = True
            elif self.autoskipuncached:
                # Auto-skip uncached: simply return nothing.
                return
            else:
                yesnocustom = control.yesnocustom_dialog(
                    heading, f_string, "Cancel", "Run in Background", "Run in Foreground",
                    defaultbutton=xbmcgui.DLG_YESNO_YES_BTN
                )
                if yesnocustom == -1 or yesnocustom == 2:
                    self.canceled = True
                    return
                runbackground = (yesnocustom == 0)
                runinforground = (yesnocustom == 1)

        try:
            resolved_cache = api.resolve_uncached_source(source, runbackground, runinforground, self.pack_select)
        except Exception as e:
            control.progressDialog.close()
            import traceback
            control.ok_dialog(control.ADDON_NAME, f'Error: {e}')
            control.log(traceback.format_exc(), 'error')
            return

        best_match = control.getBool('best_match')

        if not resolved_cache or not self.autoskipuncached:
            self.canceled = True

        if not best_match and self.autoskipuncached:
            self.canceled = False

        return resolved_cache

    def doModal(self, sources, args, pack_select):
        # Reorder sources first.
        self.sources = self.reorder_sources(sources)
        self.args = args
        # Now assign pack_select after the sources are reordered.
        self.pack_select = pack_select
        self.setProperty('release_title', str(self.sources[0]['release_title']))
        self.setProperty('debrid_provider', self.sources[0].get('debrid_provider', 'None').replace('_', ' '))
        self.setProperty('source_provider', self.sources[0]['provider'])
        self.setProperty('source_resolution', source_utils.res[self.sources[0]['quality']])
        self.setProperty('source_info', " ".join(self.sources[0]['info']))
        self.setProperty('source_type', self.sources[0]['type'])
        self.setProperty('source_size', self.sources[0]['size'])
        self.setProperty('source_seeders', str(self.sources[0].get('seeders', '')))

        if self.sources[0]['type'] in ['embed', 'direct']:
            control.setSetting('last_played_source', str(self.sources[0]['provider']) + " " + " ".join(map(str, self.sources[0]['info'])))
        else:
            control.setSetting('last_played_source', str(self.sources[0]['release_title']))

        if self.silent:
            if self.source_select_close:
                self.source_select_close()
            self.resolve(self.sources)
        else:
            super(Resolver, self).doModal()

        return self.return_data

    def onAction(self, action):
        actionID = action.getId()

        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            self.canceled = True
            self.close()


class Monitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.playbackerror = False
        self.playing = False

    def onNotification(self, sender, method, data):
        if method == 'Player.OnAVStart':
            self.playing = True
        elif method == 'Player.OnStop':
            self.playbackerror = True
        # else:
        #     control.log(f'{method} | {data}')


@hook_mimetype('application/dash+xml')
def _DASH_HOOK(item):
    if control.getBool('inputstreamadaptive.enabled'):
        stream_url = item.getPath()
        import inputstreamhelper
        is_helper = inputstreamhelper.Helper('mpd')
        if is_helper.check_inputstream():
            item.setProperty('inputstream', is_helper.inputstream_addon)
            if control.kodi_version < 20.9:
                item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
                item.setContentLookup(False)
            if '|' in stream_url:
                stream_url, headers = stream_url.split('|')
                item.setProperty('inputstream.adaptive.stream_headers', headers)
                if control.kodi_version > 21.8:
                    item.setProperty('inputstream.adaptive.common_headers', headers)
                else:
                    item.setProperty('inputstream.adaptive.stream_params', headers)
                    item.setProperty('inputstream.adaptive.manifest_headers', headers)
        else:
            raise Exception("InputStream Adaptive is not supported.")
    return item


@hook_mimetype('application/vnd.apple.mpegurl')
def _HLS_HOOK(item):
    if control.getBool('inputstreamadaptive.enabled'):
        stream_url = item.getPath()
        import inputstreamhelper
        is_helper = inputstreamhelper.Helper('hls')
        if is_helper.check_inputstream():
            item.setProperty('inputstream', is_helper.inputstream_addon)
            if control.kodi_version < 20.9:
                item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                item.setProperty('MimeType', 'application/vnd.apple.mpegurl')
                item.setMimeType('application/vnd.apple.mpegstream_url')
                item.setContentLookup(False)
            if '|' in stream_url:
                stream_url, headers = stream_url.split('|')
                item.setProperty('inputstream.adaptive.stream_headers', headers)
                if control.kodi_version > 21.8:
                    item.setProperty('inputstream.adaptive.common_headers', headers)
                else:
                    item.setProperty('inputstream.adaptive.stream_params', headers)
                    item.setProperty('inputstream.adaptive.manifest_headers', headers)

    return item


@hook_mimetype('video/MP2T')
def _HLS2_HOOK(item):
    if control.getBool('inputstreamadaptive.enabled'):
        stream_url = item.getPath()
        import inputstreamhelper
        is_helper = inputstreamhelper.Helper('hls')
        if is_helper.check_inputstream():
            item.setProperty('inputstream', is_helper.inputstream_addon)
            if control.kodi_version < 20.9:
                item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                item.setProperty('MimeType', 'application/vnd.apple.mpegurl')
                item.setMimeType('application/vnd.apple.mpegstream_url')
                item.setContentLookup(False)
            if '|' in stream_url:
                stream_url, headers = stream_url.split('|')
                item.setProperty('inputstream.adaptive.stream_headers', headers)
                if control.kodi_version > 21.8:
                    item.setProperty('inputstream.adaptive.common_headers', headers)
                else:
                    item.setProperty('inputstream.adaptive.stream_params', headers)
                    item.setProperty('inputstream.adaptive.manifest_headers', headers)

    return item
