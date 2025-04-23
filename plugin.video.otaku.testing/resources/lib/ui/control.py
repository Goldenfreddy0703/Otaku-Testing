import random
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs
import os
import sys
import json
import shutil

from urllib import parse

try:
    HANDLE = int(sys.argv[1])
except IndexError:
    HANDLE = 0

addonInfo = xbmcaddon.Addon().getAddonInfo
ADDON_ID = addonInfo('id')
ADDON = xbmcaddon.Addon(ADDON_ID)
settings = ADDON.getSettings()
language = ADDON.getLocalizedString
addonInfo = ADDON.getAddonInfo
ADDON_NAME = addonInfo('name')
ADDON_VERSION = addonInfo('version')
ADDON_ICON = addonInfo('icon')
OTAKU_FANART = addonInfo('fanart')
ADDON_PATH = ADDON.getAddonInfo('path')
pathExists = xbmcvfs.exists
dataPath = xbmcvfs.translatePath(addonInfo('profile'))
kodi_version = float(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')[:4])

CONTEXT_ADDON_ID = 'context.otaku.testing'
CONTEXT_ADDON = xbmcaddon.Addon(CONTEXT_ADDON_ID)
CONTEXT_ADDON_PATH = CONTEXT_ADDON.getAddonInfo('path')
infoDB = os.path.join(CONTEXT_ADDON_PATH, 'info.db')

cacheFile = os.path.join(dataPath, 'cache.db')
searchHistoryDB = os.path.join(dataPath, 'search.db')
malSyncDB = os.path.join(dataPath, 'malSync.db')
mappingDB = os.path.join(dataPath, 'mappings.db')
migrationSettings = os.path.join(dataPath, 'migration.json')

maldubFile = os.path.join(dataPath, 'mal_dub.json')
downloads_json = os.path.join(dataPath, 'downloads.json')
completed_json = os.path.join(dataPath, 'completed.json')
genre_json = os.path.join(dataPath, 'genres.json')
sort_options_json = os.path.join(dataPath, 'sort_options.json')
embeds_json = os.path.join(dataPath, 'embeds.json')
simkl_calendar_json = os.path.join(dataPath, 'simkl_calendar.json')
anilist_calendar_json = os.path.join(dataPath, 'anilist_calendar.json')
mal_calendar_json = os.path.join(dataPath, 'mal_calendar.json')

IMAGES_PATH = os.path.join(ADDON_PATH, 'resources', 'images')
OTAKU_LOGO_PATH = os.path.join(ADDON_PATH, 'resources', 'images', 'trans-goku.png')
OTAKU_LOGO2_PATH = os.path.join(ADDON_PATH, 'resources', 'images', 'trans-goku-small.png')
OTAKU_LOGO3_PATH = os.path.join(ADDON_PATH, 'resources', 'images', 'trans-goku-large.png')
OTAKU_ICONS_PATH = os.path.join(CONTEXT_ADDON_PATH, 'resources', 'images', 'icons', ADDON.getSetting("interface.icons"))
OTAKU_GENRE_PATH = os.path.join(CONTEXT_ADDON_PATH, 'resources', 'images', 'genres')

dialogWindow = xbmcgui.WindowDialog
homeWindow = xbmcgui.Window(10000)
menuItem = xbmcgui.ListItem
execute = xbmc.executebuiltin
get_region = xbmc.getRegion
trakt_gmt_format = '%Y-%m-%dT%H:%M:%S.000Z'
progressDialog = xbmcgui.DialogProgress()
playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
sleep = xbmc.sleep


def closeBusyDialog():
    if xbmc.getCondVisibility('Window.IsActive(busydialog)'):
        execute('Dialog.Close(busydialog)')
    if xbmc.getCondVisibility('Window.IsActive(busydialognocancel)'):
        execute('Dialog.Close(busydialognocancel)')


def log(msg, level="info"):
    if level == 'info':
        level = xbmc.LOGINFO
    elif level == 'warning':
        level = xbmc.LOGWARNING
    elif level == 'error':
        level = xbmc.LOGERROR
    else:
        level = xbmc.LOGNONE
    xbmc.log(f'{ADDON_NAME.upper()} ({HANDLE}): {msg}', level)


def bin(s):
    return s.encode('latin-1')


def enabled_debrid():
    debrids = ['realdebrid', 'debridlink', 'alldebrid', 'premiumize', 'torbox', 'easydebrid']
    return {x: getSetting(f'{x}.token') != '' and getBool(f'{x}.enabled') for x in debrids}


def enabled_cloud():
    clouds = ['realdebrid', 'alldebrid', 'premiumize', 'torbox']
    return {x: getSetting(f'{x}.token') != '' and getBool(f'{x}.cloudInspection') for x in clouds}


def enabled_watchlists():
    watchlists = ['anilist', 'kitsu', 'mal', 'simkl']
    return [x for x in watchlists if getSetting(f'{x}.token') != '' and getBool(f'{x}.enabled')]


def watchlist_to_update():
    if getBool('watchlist.update.enabled'):
        flavor = getSetting('watchlist.update.flavor').lower()
        if getBool('%s.enabled' % flavor):
            return flavor


def copy2clip(txt):
    platform = sys.platform
    if platform == 'win32':
        try:
            os.system('echo %s|clip' % txt)
            return True
        except AttributeError:
            pass
    return False


def colorstr(text, color='deepskyblue'):
    return f"[COLOR {color}]{text}[/COLOR]"


def refresh():
    execute('Container.Refresh')


def getSetting(key):
    return ADDON.getSetting(key)


def getBool(key):
    return ADDON.getSettingBool(key)


def getInt(key):
    return ADDON.getSettingInt(key)


def getStr(key):
    return ADDON.getSettingString(key)


def getStringList(settingid):
    return settings.getStringList(settingid)


def setSetting(settingid, value):
    ADDON.setSetting(settingid, value)


def setBool(settingid, value):
    ADDON.setSettingBool(settingid, value)


def setInt(settingid, value):
    ADDON.setSettingInt(settingid, value)


def setStr(settingid, value):
    ADDON.setSettingString(settingid, value)


def setStringList(settingid, value):
    return settings.setStringList(settingid, value)


def setGlobalProp(property, value):
    homeWindow.setProperty(property, str(value))


def clearGlobalProp(property):
    homeWindow.clearProperty(property)


def lang(x):
    return language(x)


def addon_url(url):
    return f"plugin://{ADDON_ID}/{url}"


def get_plugin_url():
    addon_base = addon_url('')
    return sys.argv[0][len(addon_base):]


def get_plugin_params():
    return dict(parse.parse_qsl(sys.argv[2].replace('?', '')))


def exit_code():
    if getSetting('reuselanguageinvoker.status') == 'Enabled':
        exit_(0)


def keyboard(title, text=''):
    keyboard_ = xbmc.Keyboard(text, title, False)
    keyboard_.doModal()
    if keyboard_.isConfirmed():
        return keyboard_.getText()
    return keyboard_.getText() if keyboard_.isConfirmed() else ""


def closeAllDialogs():
    execute('Dialog.Close(all,true)')


def ok_dialog(title, text):
    return xbmcgui.Dialog().ok(title, text)


def textviewer_dialog(title, text):
    xbmcgui.Dialog().textviewer(title, text)


def yesno_dialog(title, text, nolabel=None, yeslabel=None):
    return xbmcgui.Dialog().yesno(title, text, nolabel, yeslabel)


def yesnocustom_dialog(title, text, customlabel='', nolabel='', yeslabel='', autoclose=0, defaultbutton=0):
    return xbmcgui.Dialog().yesnocustom(title, text, customlabel, nolabel, yeslabel, autoclose, defaultbutton)


def notify(title, text, icon=OTAKU_LOGO3_PATH, time=5000, sound=True):
    xbmcgui.Dialog().notification(title, text, icon, time, sound)


def input_dialog(title, input_='', option=0):
    return xbmcgui.Dialog().input(title, input_, option)


def multiselect_dialog(title, dialog_list, preselect=None):
    return xbmcgui.Dialog().multiselect(title, dialog_list, preselect=preselect)


def select_dialog(title, dialog_list):
    return xbmcgui.Dialog().select(title, dialog_list)


def context_menu(context_list):
    return xbmcgui.Dialog().contextmenu(context_list)


def browse(type_, heading, shares, mask=''):
    return xbmcgui.Dialog().browse(type_, heading, shares, mask)


def set_videotags(li, info):
    vinfo: xbmc.InfoTagVideo = li.getVideoInfoTag()
    if title := info.get('title'):
        vinfo.setTitle(title)
    if media_type := info.get('mediatype'):
        vinfo.setMediaType(media_type)
    if tvshow_title := info.get('tvshowtitle'):
        vinfo.setTvShowTitle(tvshow_title)
    if plot := info.get('plot'):
        vinfo.setPlot(plot)
    if year := info.get('year'):
        vinfo.setYear(int(year))
    if premiered := info.get('premiered'):
        vinfo.setPremiered(premiered)
    if status := info.get('status'):
        vinfo.setTvShowStatus(status)
    if genre := info.get('genre'):
        vinfo.setGenres(genre)
    if mpaa := info.get('mpaa'):
        vinfo.setMpaa(mpaa)
    if rating := info.get('rating'):
        if isinstance(rating, dict):
            vinfo.setRating(rating.get('score', 0), rating.get('votes', 0))
        else:
            vinfo.setRating(0, 0)
    if season := info.get('season'):
        vinfo.setSeason(int(season))
    if episode := info.get('episode'):
        vinfo.setEpisode(int(episode))
    if aired := info.get('aired'):
        vinfo.setFirstAired(aired)
    if playcount := info.get('playcount'):
        vinfo.setPlaycount(playcount)
    if duration := info.get('duration'):
        vinfo.setDuration(duration)
    if code := info.get('code'):
        vinfo.setProductionCode(code)
    if studio := info.get('studio'):
        vinfo.setStudios(studio)
    if cast := info.get('cast'):
        vinfo.setCast([xbmc.Actor(c['name'], c['role'], c['index'], c['thumbnail']) for c in cast])
    if country := info.get('country'):
        vinfo.setCountries(country)
    if originaltitle := info.get('OriginalTitle'):
        vinfo.setOriginalTitle(originaltitle)
    if trailer := info.get('trailer'):
        vinfo.setTrailer(trailer)

    if uniqueids := info.get('UniqueIDs'):
        uniqueids = {key: str(value) for key, value in uniqueids.items()}
        vinfo.setUniqueIDs(uniqueids)
        if 'imdb' in uniqueids:
            vinfo.setIMDBNumber(uniqueids['imdb'])
        for key, value in uniqueids.items():
            if value is not None:
                li.setProperty(key, str(value))

    if resume := info.get('resume'):
        vinfo.setResumePoint(float(resume), 1)


def jsonrpc(json_data):
    return json.loads(xbmc.executeJSONRPC(json.dumps(json_data)))


def xbmc_add_dir(name, url, art, info, draw_cm, bulk_add, isfolder, isplayable):
    u = addon_url(url)
    liz = xbmcgui.ListItem(name, offscreen=True)
    if info:
        set_videotags(liz, info)
    if draw_cm:
        cm = [(x[0], f'RunPlugin(plugin://{ADDON_ID}/{x[1]}/{url})') for x in draw_cm]
        liz.addContextMenuItems(cm)
    if not art.get('fanart') or settingids.fanart_disable:
        art['fanart'] = OTAKU_FANART
    else:
        if isinstance(art['fanart'], list):
            if settingids.fanart_select:
                if info.get('UniqueIDs', {}).get('mal_id'):
                    fanart_select = getSetting(f'fanart.select.{info["UniqueIDs"]["mal_id"]}')
                    art['fanart'] = fanart_select if fanart_select else random.choice(art['fanart'])
                else:
                    art['fanart'] = OTAKU_FANART
            else:
                art['fanart'] = random.choice(art['fanart'])

    if settingids.clearlogo_disable:
        art['clearlogo'] = OTAKU_ICONS_PATH
    if isplayable:
        art['tvshow.poster'] = art.pop('poster')
        liz.setProperties({'Video': 'true', 'IsPlayable': 'true'})
    liz.setArt(art)
    return u, liz, isfolder if bulk_add else xbmcplugin.addDirectoryItem(HANDLE, u, liz, isfolder)


def bulk_draw_items(video_data):
    list_items = bulk_dir_list(video_data, True)
    return xbmcplugin.addDirectoryItems(HANDLE, list_items)


def draw_items(video_data, content_type=''):
    if len(video_data) > 99:
        bulk_draw_items(video_data)
    else:
        for vid in video_data:
            if vid:
                xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['info'], vid['cm'], False, vid['isfolder'], vid['isplayable'])
    if content_type:
        xbmcplugin.setContent(HANDLE, content_type)
    if content_type == 'episodes':
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE, "%H. %T", "%R | %P")
    elif content_type == 'tvshows':
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE, "%L", "%R")
    xbmcplugin.endOfDirectory(HANDLE, True, False, True)
    xbmc.sleep(100)
    if content_type == 'episodes':
        for _ in range(20):
            if xbmc.getCondVisibility("Container.HasFiles"):
                break
            xbmc.sleep(100)
    if getBool('interface.viewtype'):
        if getBool('interface.viewidswitch'):
            # Use integer view types
            if content_type == '' or content_type == 'addons':
                xbmc.executebuiltin('Container.SetViewMode(%d)' % int(getSetting('interface.addon.view.id')))
            elif content_type == 'tvshows':
                xbmc.executebuiltin('Container.SetViewMode(%d)' % int(getSetting('interface.show.view.id')))
            elif content_type == 'episodes':
                xbmc.executebuiltin('Container.SetViewMode(%d)' % int(getSetting('interface.episode.view.id')))
        else:
            # Use optional view types
            if content_type == '' or content_type == 'addons':
                xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.addon.view')))
            elif content_type == 'tvshows':
                xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.show.view')))
            elif content_type == 'episodes':
                xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.episode.view')))

    # move to episode position currently watching
    if content_type == "episodes" and settingids.smart_scroll:
        try:
            num_watched = int(xbmc.getInfoLabel("Container.TotalWatched"))
            total_ep = int(xbmc.getInfoLabel('Container(id).NumItems'))
            total_items = int(xbmc.getInfoLabel('Container(id).NumAllItems'))
            if total_items == total_ep + 1:
                num_watched += 1
                total_ep += 1
        except ValueError:
            return
        if total_ep > num_watched > 0:
            xbmc.executebuiltin('Action(firstpage)')
            for _ in range(num_watched):
                if getInt('smart.scroll.direction') == 0:
                    xbmc.executebuiltin('Action(Down)')
                else:
                    xbmc.executebuiltin('Action(Right)')


def bulk_dir_list(video_data, bulk_add=True):
    return [xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['info'], vid['cm'], bulk_add, vid['isfolder'], vid['isplayable']) for vid in video_data if vid]


def get_view_type(viewtype):
    viewTypes = {
        'Default': 50,
        'Poster': 51,
        'Icon Wall': 52,
        'Shift': 53,
        'Info Wall': 54,
        'Wide List': 55,
        'Wall': 500,
        'Banner': 501,
        'Fanart': 502,
        'List': 0
    }
    return viewTypes[viewtype]


def clear_settings(silent=False):
    from resources.lib.ui.database_sync import SyncDatabase
    if not silent:
        confirm = yesno_dialog(ADDON_NAME, lang(30034))
        if confirm == 0:
            return

    if os.path.exists(dataPath):
        shutil.rmtree(dataPath)

    os.mkdir(dataPath)
    refresh()

    if getSetting('version') != '0.5.43':
        SyncDatabase().re_build_database(True)


def exit_(code):
    sys.exit(code)


def is_addon_visible():
    return xbmc.getInfoLabel('Container.PluginName') == 'plugin.video.otaku.testing'


def abort_requested():
    monitor = xbmc.Monitor()
    abort_requested_ = monitor.abortRequested()
    del monitor
    return abort_requested_


def wait_for_abort(timeout=1.0):
    monitor = xbmc.Monitor()
    abort_requested_ = monitor.waitForAbort(timeout)
    del monitor
    return abort_requested_


def arc4(t, n):
    u = 0
    h = ''
    s = list(range(256))
    for e in range(256):
        x = t[e % len(t)]
        u = (u + s[e] + (x if isinstance(x, int) else ord(x))) % 256
        s[e], s[u] = s[u], s[e]

    e = u = 0
    for c in range(len(n)):
        e = (e + 1) % 256
        u = (u + s[e]) % 256
        s[e], s[u] = s[u], s[e]
        h += chr((n[c] if isinstance(n[c], int) else ord(n[c])) ^ s[(s[e] + s[u]) % 256])
    return h


def print(string, *args):
    for i in list(args):
        string = f'{string} {i}'
    textviewer_dialog('print', f'{string}')
    del args, string


class SettingIDs:
    def __init__(self):
        # Bools
        self.showuncached = getBool('show.uncached')
        self.smart_scroll = getBool('general.smart.scroll.enable')
        self.clearlogo_disable = getBool('interface.clearlogo.disable')
        self.fanart_disable = getBool('interface.fanart.disable')
        self.watchlist_sync = getBool('watchlist.sync.enabled')
        self.filler = getBool('jz.filler')
        self.clean_titles = getBool('interface.cleantitles')
        self.terminateoncloud = getBool('general.terminate.oncloud')
        self.terminateonlocal = getBool('general.terminate.onlocal')
        self.dubonly = getBool("divflavors.dubonly")
        self.showdub = getBool("divflavors.showdub")
        self.watchlist_data = getBool('interface.watchlist.data')
        self.fanart_select = getBool('context.otaku.testing.fanartselect')

        # Ints

        # Str
        self.browser_api = getStr('browser.api')


settingids = SettingIDs()
