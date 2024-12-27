import threading

from resources.lib.ui import database
from resources.lib.indexers import tmdb, fanart


def collect_meta(anime_list):
    threads = []
    for anime in anime_list:
        if 'media' in anime.keys():
            anime = anime.get('media')

        if 'entry' in anime.keys():
            anime = anime.get('entry')

        mal_id = anime.get('idMal') or anime.get('mal_id')

        if not mal_id:
            continue

        if not database.get_show_meta(mal_id):
            if (anime.get('format') or anime.get('type')) in ['MOVIE', 'ONA', 'OVA', 'SPECIAL', 'Movie', 'Special'] and anime.get('episodes') == 1:
                mtype = 'movies'
            else:
                mtype = 'tv'
            t = threading.Thread(target=update_meta, args=(mal_id, mtype))
            t.start()
            threads.append(t)
    for thread in threads:
        thread.join()


def update_meta(mal_id, mtype='tv'):
    meta_ids = database.get_mappings(mal_id, 'mal_id')
    art = fanart.getArt(meta_ids, mtype)
    if not art:
        art = tmdb.getArt(meta_ids, mtype)
    elif 'fanart' not in art.keys():
        art2 = tmdb.getArt(meta_ids, mtype)
        if art2.get('fanart'):
            art['fanart'] = art2['fanart']
    database.update_show_meta(mal_id, meta_ids, art)