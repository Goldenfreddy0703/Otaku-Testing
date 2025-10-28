import concurrent.futures

from resources.lib.endpoints import fanart, tmdb, tvdb
from resources.lib.ui import database, control


def collect_meta(anime_list):
    # Prepare list of anime that need metadata
    anime_to_fetch = []

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
            anime_to_fetch.append((mal_id, mtype))

    # Fetch metadata in parallel with controlled thread pool (max 8 workers)
    if anime_to_fetch:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(update_meta, mal_id, mtype) for mal_id, mtype in anime_to_fetch]
            # Wait for all to complete
            concurrent.futures.wait(futures)


def update_meta(mal_id, mtype='tv'):
    """
    Fetch and combine artwork from all providers (Fanart.tv, TMDB, TVDB)
    """
    meta_ids = database.get_mappings(mal_id, 'mal_id')

    # Scrape art from all providers in parallel for faster performance
    def fetch_fanart():
        try:
            return fanart.getArt(meta_ids, mtype)
        except Exception as e:
            control.log(f"Fanart.tv fetch failed: {str(e)}")
            return {}

    def fetch_tmdb():
        try:
            return tmdb.getArt(meta_ids, mtype)
        except Exception as e:
            control.log(f"TMDB fetch failed: {str(e)}")
            return {}

    def fetch_tvdb():
        try:
            return tvdb.getArt(meta_ids, mtype)
        except Exception as e:
            control.log(f"TVDB fetch failed: {str(e)}")
            return {}

    # Fetch from all providers concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        fanart_future = executor.submit(fetch_fanart)
        tmdb_future = executor.submit(fetch_tmdb)
        tvdb_future = executor.submit(fetch_tvdb)

        # Wait for all to complete
        concurrent.futures.wait([fanart_future, tmdb_future, tvdb_future])

        fanart_art = fanart_future.result()
        tmdb_art = tmdb_future.result()
        tvdb_art = tvdb_future.result()

    # Combine art from all providers
    combined_art = merge_artwork(fanart_art, tmdb_art, tvdb_art)

    database.update_show_meta(mal_id, meta_ids, combined_art)


def merge_artwork(fanart_art, tmdb_art, tvdb_art):
    """
    Merge artwork from multiple providers, combining lists and preferring quality sources.
    For clearlogo, maintain language preference logic.
    """
    merged = {}

    # Merge fanart (backgrounds)
    fanart_images = []
    fanart_images.extend(fanart_art.get('fanart', []))
    fanart_images.extend(tmdb_art.get('fanart', []))
    fanart_images.extend(tvdb_art.get('fanart', []))
    if fanart_images:
        merged['fanart'] = fanart_images

    # Merge thumbs
    thumb_images = []
    thumb_images.extend(fanart_art.get('thumb', []))
    thumb_images.extend(tmdb_art.get('thumb', []))
    thumb_images.extend(tvdb_art.get('thumb', []))
    if thumb_images:
        merged['thumb'] = thumb_images

    # Merge clearart
    clearart_images = []
    clearart_images.extend(fanart_art.get('clearart', []))
    clearart_images.extend(tmdb_art.get('clearart', []))
    clearart_images.extend(tvdb_art.get('clearart', []))
    if clearart_images:
        merged['clearart'] = clearart_images

    # Merge clearlogo with language preference
    # Each provider already returns language-filtered logos, so we combine them
    clearlogo_images = []
    clearlogo_images.extend(fanart_art.get('clearlogo', []))
    clearlogo_images.extend(tmdb_art.get('clearlogo', []))
    clearlogo_images.extend(tvdb_art.get('clearlogo', []))
    if clearlogo_images:
        # Remove duplicates while preserving order
        seen = set()
        unique_logos = []
        for logo in clearlogo_images:
            if logo not in seen:
                seen.add(logo)
                unique_logos.append(logo)
        merged['clearlogo'] = unique_logos

    return merged
