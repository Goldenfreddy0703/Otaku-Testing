import pickle

from resources.lib.indexers import simkl, anizip, jikanmoe, kitsu, anidb
from resources.lib.ui import control, database

if control.settingids.browser_api == 'otaku':
    from resources.lib.OtakuBrowser import OtakuBrowser
    BROWSER = OtakuBrowser()
elif control.settingids.browser_api == 'mal':
    from resources.lib.MalBrowser import MalBrowser
    BROWSER = MalBrowser()
else:
    from resources.lib.AniListBrowser import AniListBrowser
    BROWSER = AniListBrowser()


def get_anime_init(mal_id):
    show_meta = database.get_show_meta(mal_id)
    if not show_meta:
        BROWSER.get_anime(mal_id)
        show_meta = database.get_show_meta(mal_id)
        if not show_meta:
            return [], 'episodes'

    if control.getBool('override.meta.api'):
        meta_api = control.getSetting('meta.api')
        if meta_api == 'simkl':
            data = simkl.SIMKLAPI().get_episodes(mal_id, show_meta)
        elif meta_api == 'anizip':
            data = anizip.ANIZIPAPI().get_episodes(mal_id, show_meta)
        elif meta_api == 'jikanmoe':
            data = jikanmoe.JikanAPI().get_episodes(mal_id, show_meta)
        elif meta_api == 'anidb':
            data = anidb.ANIDBAPI().get_episodes(mal_id, show_meta)
        elif meta_api == 'kitsu':
            data = kitsu.KitsuAPI().get_episodes(mal_id, show_meta)

    else:
        data = simkl.SIMKLAPI().get_episodes(mal_id, show_meta)
        if not data:
            data = anizip.ANIZIPAPI().get_episodes(mal_id, show_meta)
        if not data:
            data = jikanmoe.JikanAPI().get_episodes(mal_id, show_meta)
        if not data:
            data = anidb.ANIDBAPI().get_episodes(mal_id, show_meta)
        if not data:
            data = kitsu.KitsuAPI().get_episodes(mal_id, show_meta)
        if not data:
            data = []
    return data, 'episodes'


def get_sources(mal_id, episode, media_type, rescrape=False, source_select=False, silent=False):
    from resources.lib import pages
    if not (show := database.get_show(mal_id)):
        show = BROWSER.get_anime(mal_id)
    kodi_meta = pickle.loads(show['kodi_meta'])
    actionArgs = {
        'query': kodi_meta['query'],
        'mal_id': mal_id,
        'episode': episode,
        'episodes': kodi_meta['episodes'],
        'status': kodi_meta['status'],
        'duration': kodi_meta['duration'],
        'media_type': media_type,
        'rescrape': rescrape,
        'source_select': source_select,
        'silent': silent
    }

    sources = pages.getSourcesHelper(actionArgs)
    return sources
