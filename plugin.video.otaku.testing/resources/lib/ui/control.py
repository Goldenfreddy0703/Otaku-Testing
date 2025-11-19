# -----------------------------
# LazyModule Wrapper
# -----------------------------
class LazyModule:
    def __init__(self, loader):
        self._loader = loader
        self._module = None

    def _load(self):
        if self._module is None:
            self._module = self._loader()
        return self._module

    def __getattr__(self, name):
        module = self._load()
        return getattr(module, name)
    
# -----------------------------
# Lazy-loaded Modules
# -----------------------------
array = LazyModule(lambda: __import__("array"))
ast = LazyModule(lambda: __import__("ast"))
base64 = LazyModule(lambda: __import__("base64"))
binascii = LazyModule(lambda: __import__("binascii"))
bs4 = LazyModule(lambda: __import__("bs4"))
codecs = LazyModule(lambda: __import__("codecs"))
concurrent = LazyModule(lambda: __import__("concurrent"))
copy = LazyModule(lambda: __import__("copy"))
datetime = LazyModule(lambda: __import__("datetime"))
difflib = LazyModule(lambda: __import__("difflib"))
functools = LazyModule(lambda: __import__("functools"))
gzip = LazyModule(lambda: __import__("gzip"))
hashlib = LazyModule(lambda: __import__("hashlib"))
html = LazyModule(lambda: __import__("html"))
http = LazyModule(lambda: __import__("http"))
inputstreamhelper = LazyModule(lambda: __import__("inputstreamhelper"))
io = LazyModule(lambda: __import__("io"))
itertools = LazyModule(lambda: __import__("itertools"))
json = LazyModule(lambda: __import__("json"))
math = LazyModule(lambda: __import__("math"))
operator = LazyModule(lambda: __import__("operator"))
os = LazyModule(lambda: __import__("os"))
pathlib = LazyModule(lambda: __import__("pathlib"))
pickle = LazyModule(lambda: __import__("pickle"))
platform = LazyModule(lambda: __import__("platform"))
random = LazyModule(lambda: __import__("random"))
re = LazyModule(lambda: __import__("re"))
resources = LazyModule(lambda: __import__("resources"))
service = LazyModule(lambda: __import__("service"))
shutil = LazyModule(lambda: __import__("shutil"))
sqlite3 = LazyModule(lambda: __import__("sqlite3"))
ssl = LazyModule(lambda: __import__("ssl"))
string = LazyModule(lambda: __import__("string"))
struct = LazyModule(lambda: __import__("struct"))
sys = LazyModule(lambda: __import__("sys"))
threading = LazyModule(lambda: __import__("threading"))
time = LazyModule(lambda: __import__("time"))
top = LazyModule(lambda: __import__("top"))
traceback = LazyModule(lambda: __import__("traceback"))
urllib = LazyModule(lambda: __import__("urllib"))
xbmc = LazyModule(lambda: __import__("xbmc"))
xbmcaddon = LazyModule(lambda: __import__("xbmcaddon"))
xbmcgui = LazyModule(lambda: __import__("xbmcgui"))
xbmcplugin = LazyModule(lambda: __import__("xbmcplugin"))
xbmcvfs = LazyModule(lambda: __import__("xbmcvfs"))
xml = LazyModule(lambda: __import__("xml"))
cleanup_whitespace = LazyModule(lambda: __import__("cleanup_whitespace"))
default = LazyModule(lambda: __import__("default"))
generate_lazy_modules_and_classes = LazyModule(lambda: __import__("generate_lazy_modules_and_classes"))
renumber_string_ids = LazyModule(lambda: __import__("renumber_string_ids"))
resources = LazyModule(lambda: __import__("resources"))
lib = LazyModule(lambda: __import__("resources.lib"))
AniListBrowser = LazyModule(lambda: __import__("resources.lib.AniListBrowser"))
AnimeSchedule = LazyModule(lambda: __import__("resources.lib.AnimeSchedule"))
Main = LazyModule(lambda: __import__("resources.lib.Main"))
MalBrowser = LazyModule(lambda: __import__("resources.lib.MalBrowser"))
MetaBrowser = LazyModule(lambda: __import__("resources.lib.MetaBrowser"))
OtakuBrowser = LazyModule(lambda: __import__("resources.lib.OtakuBrowser"))
WatchlistFlavor = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor"))
AniList = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor.AniList"))
Kitsu = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor.Kitsu"))
MyAnimeList = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor.MyAnimeList"))
Simkl = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor.Simkl"))
WatchlistFlavorBase = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor.WatchlistFlavorBase"))
WatchlistIntegration = LazyModule(lambda: __import__("resources.lib.WatchlistIntegration"))
debrid = LazyModule(lambda: __import__("resources.lib.debrid"))
all_debrid = LazyModule(lambda: __import__("resources.lib.debrid.all_debrid"))
debrid_link = LazyModule(lambda: __import__("resources.lib.debrid.debrid_link"))
easydebrid = LazyModule(lambda: __import__("resources.lib.debrid.easydebrid"))
premiumize = LazyModule(lambda: __import__("resources.lib.debrid.premiumize"))
real_debrid = LazyModule(lambda: __import__("resources.lib.debrid.real_debrid"))
torbox = LazyModule(lambda: __import__("resources.lib.debrid.torbox"))
endpoints = LazyModule(lambda: __import__("resources.lib.endpoints"))
anidb = LazyModule(lambda: __import__("resources.lib.endpoints.anidb"))
anilist = LazyModule(lambda: __import__("resources.lib.endpoints.anilist"))
anime_filler = LazyModule(lambda: __import__("resources.lib.endpoints.anime_filler"))
anime_skip = LazyModule(lambda: __import__("resources.lib.endpoints.anime_skip"))
animeschedule = LazyModule(lambda: __import__("resources.lib.endpoints.animeschedule"))
aniskip = LazyModule(lambda: __import__("resources.lib.endpoints.aniskip"))
fanart = LazyModule(lambda: __import__("resources.lib.endpoints.fanart"))
malsync = LazyModule(lambda: __import__("resources.lib.endpoints.malsync"))
mdblist = LazyModule(lambda: __import__("resources.lib.endpoints.mdblist"))
teamup = LazyModule(lambda: __import__("resources.lib.endpoints.teamup"))
tmdb = LazyModule(lambda: __import__("resources.lib.endpoints.tmdb"))
tvdb = LazyModule(lambda: __import__("resources.lib.endpoints.tvdb"))
indexers = LazyModule(lambda: __import__("resources.lib.indexers"))
anidb = LazyModule(lambda: __import__("resources.lib.indexers.anidb"))
anizip = LazyModule(lambda: __import__("resources.lib.indexers.anizip"))
jikanmoe = LazyModule(lambda: __import__("resources.lib.indexers.jikanmoe"))
kitsu = LazyModule(lambda: __import__("resources.lib.indexers.kitsu"))
otaku = LazyModule(lambda: __import__("resources.lib.indexers.otaku"))
simkl = LazyModule(lambda: __import__("resources.lib.indexers.simkl"))
pages = LazyModule(lambda: __import__("resources.lib.pages"))
animepahe = LazyModule(lambda: __import__("resources.lib.pages.animepahe"))
animetosho = LazyModule(lambda: __import__("resources.lib.pages.animetosho"))
animixplay = LazyModule(lambda: __import__("resources.lib.pages.animixplay"))
aniwave = LazyModule(lambda: __import__("resources.lib.pages.aniwave"))
debrid_cloudfiles = LazyModule(lambda: __import__("resources.lib.pages.debrid_cloudfiles"))
gogoanime = LazyModule(lambda: __import__("resources.lib.pages.gogoanime"))
hianime = LazyModule(lambda: __import__("resources.lib.pages.hianime"))
localfiles = LazyModule(lambda: __import__("resources.lib.pages.localfiles"))
nyaa = LazyModule(lambda: __import__("resources.lib.pages.nyaa"))
watchnixtoons2 = LazyModule(lambda: __import__("resources.lib.pages.watchnixtoons2"))
ui = LazyModule(lambda: __import__("resources.lib.ui"))
BrowserBase = LazyModule(lambda: __import__("resources.lib.ui.BrowserBase"))
client = LazyModule(lambda: __import__("resources.lib.ui.client"))
database = LazyModule(lambda: __import__("resources.lib.ui.database"))
database_sync = LazyModule(lambda: __import__("resources.lib.ui.database_sync"))
divide_flavors = LazyModule(lambda: __import__("resources.lib.ui.divide_flavors"))
embed_extractor = LazyModule(lambda: __import__("resources.lib.ui.embed_extractor"))
get_meta = LazyModule(lambda: __import__("resources.lib.ui.get_meta"))
jscrypto = LazyModule(lambda: __import__("resources.lib.ui.jscrypto"))
jscrypto = LazyModule(lambda: __import__("resources.lib.ui.jscrypto.jscrypto"))
pkcs7 = LazyModule(lambda: __import__("resources.lib.ui.jscrypto.pkcs7"))
pyaes = LazyModule(lambda: __import__("resources.lib.ui.jscrypto.pyaes"))
jsunpack = LazyModule(lambda: __import__("resources.lib.ui.jsunpack"))
megacloud_extractor = LazyModule(lambda: __import__("resources.lib.ui.megacloud_extractor"))
migrate_artwork = LazyModule(lambda: __import__("resources.lib.ui.migrate_artwork"))
player = LazyModule(lambda: __import__("resources.lib.ui.player"))
pyaes = LazyModule(lambda: __import__("resources.lib.ui.pyaes"))
aes = LazyModule(lambda: __import__("resources.lib.ui.pyaes.aes"))
blockfeeder = LazyModule(lambda: __import__("resources.lib.ui.pyaes.blockfeeder"))
util = LazyModule(lambda: __import__("resources.lib.ui.pyaes.util"))
router = LazyModule(lambda: __import__("resources.lib.ui.router"))
source_utils = LazyModule(lambda: __import__("resources.lib.ui.source_utils"))
utils = LazyModule(lambda: __import__("resources.lib.ui.utils"))
windows = LazyModule(lambda: __import__("resources.lib.windows"))
anichart = LazyModule(lambda: __import__("resources.lib.windows.anichart"))
anichart_window = LazyModule(lambda: __import__("resources.lib.windows.anichart_window"))
base_window = LazyModule(lambda: __import__("resources.lib.windows.base_window"))
download_manager = LazyModule(lambda: __import__("resources.lib.windows.download_manager"))
filter_select = LazyModule(lambda: __import__("resources.lib.windows.filter_select"))
get_sources_window = LazyModule(lambda: __import__("resources.lib.windows.get_sources_window"))
playing_next = LazyModule(lambda: __import__("resources.lib.windows.playing_next"))
resolver = LazyModule(lambda: __import__("resources.lib.windows.resolver"))
skip_intro = LazyModule(lambda: __import__("resources.lib.windows.skip_intro"))
sort_select = LazyModule(lambda: __import__("resources.lib.windows.sort_select"))
source_select = LazyModule(lambda: __import__("resources.lib.windows.source_select"))
textviewer = LazyModule(lambda: __import__("resources.lib.windows.textviewer"))
wlf_auth = LazyModule(lambda: __import__("resources.lib.windows.wlf_auth"))
service = LazyModule(lambda: __import__("service"))
symbolic_string = LazyModule(lambda: __import__("symbolic_string"))
AES = LazyModule(lambda: __import__("resources.lib.ui.jscrypto.pyaes", fromlist=["AES"]))
AES = LazyModule(lambda: __import__("resources.lib.ui.pyaes.aes", fromlist=["AES"]))
AESBlockModeOfOperation = LazyModule(lambda: __import__("resources.lib.ui.pyaes.aes", fromlist=["AESBlockModeOfOperation"]))
AESModeOfOperationCBC = LazyModule(lambda: __import__("resources.lib.ui.pyaes.aes", fromlist=["AESModeOfOperationCBC"]))
AESModeOfOperationCFB = LazyModule(lambda: __import__("resources.lib.ui.pyaes.aes", fromlist=["AESModeOfOperationCFB"]))
AESModeOfOperationCTR = LazyModule(lambda: __import__("resources.lib.ui.pyaes.aes", fromlist=["AESModeOfOperationCTR"]))
AESModeOfOperationECB = LazyModule(lambda: __import__("resources.lib.ui.pyaes.aes", fromlist=["AESModeOfOperationECB"]))
AESModeOfOperationOFB = LazyModule(lambda: __import__("resources.lib.ui.pyaes.aes", fromlist=["AESModeOfOperationOFB"]))
AESSegmentModeOfOperation = LazyModule(lambda: __import__("resources.lib.ui.pyaes.aes", fromlist=["AESSegmentModeOfOperation"]))
AESStreamModeOfOperation = LazyModule(lambda: __import__("resources.lib.ui.pyaes.aes", fromlist=["AESStreamModeOfOperation"]))
ANIDBAPI = LazyModule(lambda: __import__("resources.lib.indexers.anidb", fromlist=["ANIDBAPI"]))
ANIZIPAPI = LazyModule(lambda: __import__("resources.lib.indexers.anizip", fromlist=["ANIZIPAPI"]))
AllDebrid = LazyModule(lambda: __import__("resources.lib.debrid.all_debrid", fromlist=["AllDebrid"]))
AltWatchlistFlavorAuth = LazyModule(lambda: __import__("resources.lib.windows.wlf_auth", fromlist=["AltWatchlistFlavorAuth"]))
AniListBrowser = LazyModule(lambda: __import__("resources.lib.AniListBrowser", fromlist=["AniListBrowser"]))
AniListWLF = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor.AniList", fromlist=["AniListWLF"]))
Anichart = LazyModule(lambda: __import__("resources.lib.windows.anichart", fromlist=["Anichart"]))
Anilist = LazyModule(lambda: __import__("resources.lib.endpoints.anilist", fromlist=["Anilist"]))
AnimeScheduleCalendar = LazyModule(lambda: __import__("resources.lib.AnimeSchedule", fromlist=["AnimeScheduleCalendar"]))
BaseWindow = LazyModule(lambda: __import__("resources.lib.windows.anichart_window", fromlist=["BaseWindow"]))
BaseWindow = LazyModule(lambda: __import__("resources.lib.windows.base_window", fromlist=["BaseWindow"]))
BlockFeeder = LazyModule(lambda: __import__("resources.lib.ui.pyaes.blockfeeder", fromlist=["BlockFeeder"]))
BrowserBase = LazyModule(lambda: __import__("resources.lib.ui.BrowserBase", fromlist=["BrowserBase"]))
CBCMode = LazyModule(lambda: __import__("resources.lib.ui.jscrypto.pyaes", fromlist=["CBCMode"]))
Counter = LazyModule(lambda: __import__("resources.lib.ui.pyaes.aes", fromlist=["Counter"]))
Debrid = LazyModule(lambda: __import__("resources.lib.debrid", fromlist=["Debrid"]))
DebridLink = LazyModule(lambda: __import__("resources.lib.debrid.debrid_link", fromlist=["DebridLink"]))
Decrypter = LazyModule(lambda: __import__("resources.lib.ui.pyaes.blockfeeder", fromlist=["Decrypter"]))
DownloadManager = LazyModule(lambda: __import__("resources.lib.windows.download_manager", fromlist=["DownloadManager"]))
ECBMode = LazyModule(lambda: __import__("resources.lib.ui.jscrypto.pyaes", fromlist=["ECBMode"]))
EasyDebrid = LazyModule(lambda: __import__("resources.lib.debrid.easydebrid", fromlist=["EasyDebrid"]))
Encrypter = LazyModule(lambda: __import__("resources.lib.ui.pyaes.blockfeeder", fromlist=["Encrypter"]))
FilterSelect = LazyModule(lambda: __import__("resources.lib.windows.filter_select", fromlist=["FilterSelect"]))
GetSources = LazyModule(lambda: __import__("resources.lib.windows.get_sources_window", fromlist=["GetSources"]))
JikanAPI = LazyModule(lambda: __import__("resources.lib.indexers.jikanmoe", fromlist=["JikanAPI"]))
KitsuAPI = LazyModule(lambda: __import__("resources.lib.indexers.kitsu", fromlist=["KitsuAPI"]))
KitsuWLF = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor.Kitsu", fromlist=["KitsuWLF"]))
MDBListAPI = LazyModule(lambda: __import__("resources.lib.endpoints.mdblist", fromlist=["MDBListAPI"]))
MalBrowser = LazyModule(lambda: __import__("resources.lib.MalBrowser", fromlist=["MalBrowser"]))
Manager = LazyModule(lambda: __import__("resources.lib.windows.download_manager", fromlist=["Manager"]))
MegacloudDecryptor = LazyModule(lambda: __import__("resources.lib.ui.megacloud_extractor", fromlist=["MegacloudDecryptor"]))
Monitor = LazyModule(lambda: __import__("resources.lib.ui.player", fromlist=["Monitor"]))
Monitor = LazyModule(lambda: __import__("resources.lib.windows.resolver", fromlist=["Monitor"]))
MyAnimeListWLF = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor.MyAnimeList", fromlist=["MyAnimeListWLF"]))
NoRedirectHandler = LazyModule(lambda: __import__("resources.lib.ui.client", fromlist=["NoRedirectHandler"]))
OtakuAPI = LazyModule(lambda: __import__("resources.lib.indexers.otaku", fromlist=["OtakuAPI"]))
OtakuBrowser = LazyModule(lambda: __import__("resources.lib.OtakuBrowser", fromlist=["OtakuBrowser"]))
PKCS7Encoder = LazyModule(lambda: __import__("resources.lib.ui.jscrypto.pkcs7", fromlist=["PKCS7Encoder"]))
PlayerDialogs = LazyModule(lambda: __import__("resources.lib.ui.player", fromlist=["PlayerDialogs"]))
PlayingNext = LazyModule(lambda: __import__("resources.lib.windows.playing_next", fromlist=["PlayingNext"]))
Premiumize = LazyModule(lambda: __import__("resources.lib.debrid.premiumize", fromlist=["Premiumize"]))
RealDebrid = LazyModule(lambda: __import__("resources.lib.debrid.real_debrid", fromlist=["RealDebrid"]))
Resolver = LazyModule(lambda: __import__("resources.lib.windows.resolver", fromlist=["Resolver"]))
Response = LazyModule(lambda: __import__("resources.lib.ui.client", fromlist=["Response"]))
Route = LazyModule(lambda: __import__("resources.lib.ui.router", fromlist=["Route"]))
SIMKLAPI = LazyModule(lambda: __import__("resources.lib.indexers.simkl", fromlist=["SIMKLAPI"]))
SQL = LazyModule(lambda: __import__("resources.lib.ui.database", fromlist=["SQL"]))
Session = LazyModule(lambda: __import__("resources.lib.ui.client", fromlist=["Session"]))
SimklWLF = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor.Simkl", fromlist=["SimklWLF"]))
SkipIntro = LazyModule(lambda: __import__("resources.lib.windows.skip_intro", fromlist=["SkipIntro"]))
SortSelect = LazyModule(lambda: __import__("resources.lib.windows.sort_select", fromlist=["SortSelect"]))
SourceSelect = LazyModule(lambda: __import__("resources.lib.windows.source_select", fromlist=["SourceSelect"]))
Sources = LazyModule(lambda: __import__("resources.lib.pages", fromlist=["Sources"]))
Sources = LazyModule(lambda: __import__("resources.lib.pages.animepahe", fromlist=["Sources"]))
Sources = LazyModule(lambda: __import__("resources.lib.pages.animetosho", fromlist=["Sources"]))
Sources = LazyModule(lambda: __import__("resources.lib.pages.animixplay", fromlist=["Sources"]))
Sources = LazyModule(lambda: __import__("resources.lib.pages.aniwave", fromlist=["Sources"]))
Sources = LazyModule(lambda: __import__("resources.lib.pages.debrid_cloudfiles", fromlist=["Sources"]))
Sources = LazyModule(lambda: __import__("resources.lib.pages.gogoanime", fromlist=["Sources"]))
Sources = LazyModule(lambda: __import__("resources.lib.pages.hianime", fromlist=["Sources"]))
Sources = LazyModule(lambda: __import__("resources.lib.pages.localfiles", fromlist=["Sources"]))
Sources = LazyModule(lambda: __import__("resources.lib.pages.nyaa", fromlist=["Sources"]))
Sources = LazyModule(lambda: __import__("resources.lib.pages.watchnixtoons2", fromlist=["Sources"]))
SyncDatabase = LazyModule(lambda: __import__("resources.lib.ui.database_sync", fromlist=["SyncDatabase"]))
TextViewerXML = LazyModule(lambda: __import__("resources.lib.windows.textviewer", fromlist=["TextViewerXML"]))
TorBox = LazyModule(lambda: __import__("resources.lib.debrid.torbox", fromlist=["TorBox"]))
Unbaser = LazyModule(lambda: __import__("resources.lib.ui.jsunpack", fromlist=["Unbaser"]))
UnpackingError = LazyModule(lambda: __import__("resources.lib.ui.jsunpack", fromlist=["UnpackingError"]))
WatchlistFlavor = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor", fromlist=["WatchlistFlavor"]))
WatchlistFlavorAuth = LazyModule(lambda: __import__("resources.lib.windows.wlf_auth", fromlist=["WatchlistFlavorAuth"]))
WatchlistFlavorBase = LazyModule(lambda: __import__("resources.lib.WatchlistFlavor.WatchlistFlavorBase", fromlist=["WatchlistFlavorBase"]))
WatchlistPlayer = LazyModule(lambda: __import__("resources.lib.ui.player", fromlist=["WatchlistPlayer"]))
_BrowserProxy = LazyModule(lambda: __import__("resources.lib.MetaBrowser", fromlist=["_BrowserProxy"]))
cfcookie = LazyModule(lambda: __import__("resources.lib.ui.client", fromlist=["cfcookie"]))
ddgcookie = LazyModule(lambda: __import__("resources.lib.ui.client", fromlist=["ddgcookie"]))
hook_mimetype = LazyModule(lambda: __import__("resources.lib.windows.resolver", fromlist=["hook_mimetype"]))

# Session-based cache for artwork selections to avoid repeated random.choice() calls
_artwork_cache = {}

try:
    HANDLE = int(sys.argv[1])
except IndexError:
    print('No handle found, using default 0')
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
ADDONS_PATH = xbmcvfs.translatePath('special://home/addons/')
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
watch_history_json = os.path.join(dataPath, 'watch_history.json')
embeds_json = os.path.join(dataPath, 'embeds.json')
animeschedule_calendar_json = os.path.join(dataPath, 'animeschedule_calendar.json')

# Kodi system paths
kodi_userdata_path = xbmcvfs.translatePath('special://userdata/')
kodi_advancedsettings_path = os.path.join(kodi_userdata_path, 'advancedsettings.xml')

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
    elif level == 'debug':
        level = xbmc.LOGDEBUG
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
    """Get setting as string - kept for backward compatibility"""
    return settings.getString(key)


def getBool(key):
    """Get setting as boolean"""
    return settings.getBool(key)


def getInt(key):
    """Get setting as integer"""
    return settings.getInt(key)


def getStr(key):
    """Get setting as string"""
    return settings.getString(key)


def getNumber(key):
    """Get setting as float/number"""
    return settings.getNumber(key)


def getStringList(settingid):
    """Get setting as list of strings"""
    return settings.getStringList(settingid)


def getBoolList(settingid):
    """Get setting as list of booleans"""
    return settings.getBoolList(settingid)


def getIntList(settingid):
    """Get setting as list of integers"""
    return settings.getIntList(settingid)


def getNumberList(settingid):
    """Get setting as list of numbers"""
    return settings.getNumberList(settingid)


def setSetting(settingid, value):
    """Set setting as string - kept for backward compatibility"""
    settings.setString(settingid, str(value))


def setBool(settingid, value):
    """Set setting as boolean"""
    settings.setBool(settingid, value)


def setInt(settingid, value):
    """Set setting as integer"""
    settings.setInt(settingid, value)


def setStr(settingid, value):
    """Set setting as string"""
    settings.setString(settingid, value)


def setNumber(settingid, value):
    """Set setting as float/number"""
    settings.setNumber(settingid, value)


def setStringList(settingid, value):
    """Set setting as list of strings"""
    settings.setStringList(settingid, value)


def setBoolList(settingid, value):
    """Set setting as list of booleans"""
    settings.setBoolList(settingid, value)


def setIntList(settingid, value):
    """Set setting as list of integers"""
    settings.setIntList(settingid, value)


def setNumberList(settingid, value):
    """Set setting as list of numbers"""
    settings.setNumberList(settingid, value)


def setGlobalProp(property, value):
    homeWindow.setProperty(property, str(value))


def getGlobalProp(property):
    return homeWindow.getProperty(property)


def clearGlobalProp(property):
    homeWindow.clearProperty(property)


def lang(x):
    return language(x)


def addon_url(url):
    return f"plugin://{ADDON_ID}/{url}"


def get_plugin_url(url):
    addon_base = addon_url('')
    return url[len(addon_base):]


def get_plugin_params(param):
    return dict(parse.parse_qsl(param.replace('?', '')))


def get_payload_params(url):
    url_list = url.rsplit('?', 1)
    if len(url_list) == 1:
        url_list.append('')
    payload, params = url_list
    return get_plugin_url(payload), get_plugin_params(params)


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


def notify(title, text, icon=OTAKU_LOGO3_PATH, time=5000, sound=False):
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
    if title := info.get('title') or info.get('title_userPreferred'):
        vinfo.setTitle(title)
    if media_type := info.get('mediatype') or info.get('format'):
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
    # Check new artwork.fanart setting (inverted logic from old fanart_disable)
    artwork_fanart_enabled = getBool('artwork.fanart')

    if not art.get('fanart') or not artwork_fanart_enabled:
        art['fanart'] = OTAKU_FANART
    else:
        if isinstance(art['fanart'], list):
            if getBool('context.otaku.testing.fanartselect'):
                if info.get('UniqueIDs', {}).get('mal_id'):
                    mal_id = str(info["UniqueIDs"]["mal_id"])

                    # Check cache first
                    cache_key = f"fanart_{mal_id}"
                    if cache_key in _artwork_cache:
                        art['fanart'] = _artwork_cache[cache_key]
                    else:
                        # Get fanart selection using string lists (only once)
                        mal_ids = getStringList('fanart.mal_ids')
                        fanart_selections = getStringList('fanart.selections')

                        fanart_select = ''
                        try:
                            index = mal_ids.index(mal_id)
                            fanart_select = fanart_selections[index] if index < len(fanart_selections) else ''
                        except (ValueError, IndexError):
                            pass

                        selected = fanart_select if fanart_select else random.choice(art['fanart'])
                        _artwork_cache[cache_key] = selected
                        art['fanart'] = selected
                else:
                    art['fanart'] = OTAKU_FANART
            else:
                # Use cached random selection if available
                cache_key = f"fanart_{url}"
                if cache_key in _artwork_cache:
                    art['fanart'] = _artwork_cache[cache_key]
                else:
                    selected = random.choice(art['fanart'])
                    _artwork_cache[cache_key] = selected
                    art['fanart'] = selected
        # If fanart is already a string (pre-selected), use it directly

    # Check new artwork.clearlogo setting (inverted logic from old clearlogo_disable)
    artwork_clearlogo_enabled = getBool('artwork.clearlogo')
    if not artwork_clearlogo_enabled or not art.get('clearlogo'):
        art['clearlogo'] = OTAKU_ICONS_PATH
    # If clearlogo is already a string (pre-selected), use it directly
    # No need for random.choice() since get_meta.py pre-selects it
    if isplayable:
        art['tvshow.poster'] = art.pop('poster')
        liz.setProperties({'Video': 'true', 'IsPlayable': 'true'})
    liz.setArt(art)
    return u, liz, isfolder if bulk_add else xbmcplugin.addDirectoryItem(HANDLE, u, liz, isfolder)


def bulk_draw_items(video_data):
    list_items = bulk_dir_list(video_data, True)
    return xbmcplugin.addDirectoryItems(HANDLE, list_items)


def draw_items(video_data, content_type=''):
    # Widget rate limiting - detect if this is a widget request
    is_widget = xbmc.getInfoLabel('Container.PluginName') != ADDON_ID

    if is_widget:
        # This is a widget request - add delay to respect rate limits
        widget_delay = getInt('widgets.delay') or 1000  # Default 1 second (1000ms)
        log(f"Widget detected - adding {widget_delay}ms delay")
        xbmc.sleep(widget_delay)

    # Always use bulk directory adds for better performance (Seren-style optimization)
    bulk_draw_items(video_data)
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
                xbmc.executebuiltin('Container.SetViewMode(%d)' % getInt('interface.addon.view.id'))
            elif content_type == 'tvshows':
                xbmc.executebuiltin('Container.SetViewMode(%d)' % getInt('interface.show.view.id'))
            elif content_type == 'episodes':
                xbmc.executebuiltin('Container.SetViewMode(%d)' % getInt('interface.episode.view.id'))
        else:
            # Use optional view types
            if content_type == '' or content_type == 'addons':
                xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.addon.view')))
            elif content_type == 'tvshows':
                xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.show.view')))
            elif content_type == 'episodes':
                xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.episode.view')))

    # move to episode position currently watching
    if content_type == "episodes" and getBool('general.smart.scroll.enable'):
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
        confirm = yesno_dialog(ADDON_NAME, lang(30090))
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
