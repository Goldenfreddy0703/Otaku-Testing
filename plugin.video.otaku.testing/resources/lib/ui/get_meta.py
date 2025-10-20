import concurrent.futures

from resources.lib.endpoints import fanart, tmdb, tvdb
from resources.lib.ui import database


def collect_meta(anime_list):
    # Prepare list of anime that need metadata
    anime_to_fetch = []
    mal_ids_to_check = []

    # First pass: collect all mal_ids and their types
    for anime in anime_list:
        if 'media' in anime.keys():
            anime = anime.get('media')

        if 'entry' in anime.keys():
            anime = anime.get('entry')

        mal_id = anime.get('idMal') or anime.get('mal_id')

        if not mal_id:
            continue

        mal_ids_to_check.append(mal_id)

        # Determine media type
        if (anime.get('format') or anime.get('type')) in ['MOVIE', 'ONA', 'OVA', 'SPECIAL', 'Movie', 'Special'] and anime.get('episodes') == 1:
            mtype = 'movies'
        else:
            mtype = 'tv'
        anime_to_fetch.append((mal_id, mtype))

    # PERFORMANCE FIX: Batch check which shows already have metadata
    # Instead of 25 individual queries, do 1 batch query
    existing_meta_ids = set()
    if mal_ids_to_check:
        existing_meta_ids = database.get_existing_show_meta_ids(mal_ids_to_check)

    # Filter to only fetch shows that don't have metadata
    anime_to_fetch = [(mal_id, mtype) for mal_id, mtype in anime_to_fetch if mal_id not in existing_meta_ids]

    # Fetch metadata in parallel with controlled thread pool (max 8 workers)
    if anime_to_fetch:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(update_meta, mal_id, mtype) for mal_id, mtype in anime_to_fetch]
            # Wait for all to complete
            concurrent.futures.wait(futures)


def update_meta(mal_id, mtype='tv'):
    meta_ids = database.get_mappings(mal_id, 'mal_id')
    art = fanart.getArt(meta_ids, mtype)
    if not art:
        art = tmdb.getArt(meta_ids, mtype)
        if not art:
            art = tvdb.getArt(meta_ids, mtype)
    elif 'fanart' not in art.keys():
        art2 = tmdb.getArt(meta_ids, mtype)
        if art2.get('fanart'):
            art['fanart'] = art2['fanart']
        else:
            art3 = tvdb.getArt(meta_ids, mtype)
            if art3.get('fanart'):
                art['fanart'] = art3['fanart']

    # Update legacy shows_meta table (pickle)
    database.update_show_meta(mal_id, meta_ids, art)

    # PERFORMANCE: Also update pre-computed art in shows table for Seren-style list building
    # Get existing show data to merge art with existing pre-computed data
    show_data = database.get_show(mal_id)

    import json
    import datetime

    # Get existing pre-computed art, or start with empty dict
    existing_art = {}
    if show_data and show_data.get('art'):
        try:
            existing_art = json.loads(show_data['art'])
        except (json.JSONDecodeError, TypeError):
            pass

    # IMPORTANT: Convert list values to single URL strings (Kodi expects strings, not lists)
    # Fanart.tv/TMDB/TVDB return lists: {'fanart': [url1, url2], 'thumb': [url1]}
    # But Kodi expects strings: {'fanart': 'url1', 'thumb': 'url1'}
    art_converted = {}
    for key, value in art.items():
        if isinstance(value, list) and len(value) > 0:
            art_converted[key] = value[0]  # Use first URL from list
        elif isinstance(value, str):
            art_converted[key] = value

    # Merge new art with existing art (new art takes priority)
    merged_art = {**existing_art, **art_converted}

    # PERFORMANCE: Update the art column in shows table for Seren-style list building
    # Create minimal show entry if it doesn't exist yet (for watchlists that don't create shows)
    from resources.lib.ui.database import SQL
    from resources.lib.ui import control
    import pickle

    art_json = json.dumps(merged_art)
    last_updated = datetime.datetime.now().isoformat()

    with SQL(control.malSyncDB) as cursor:
        if show_data:
            # Show exists, just update art
            cursor.execute(
                'UPDATE shows SET art = ?, last_updated = ? WHERE mal_id = ?',
                (art_json, last_updated, mal_id)
            )
        else:
            # Show doesn't exist, create minimal entry with empty kodi_meta and anime_schedule_route
            # This ensures watchlist items have fanart available via get_show_list()
            empty_kodi_meta = pickle.dumps({})  # Empty pickle blob
            cursor.execute(
                'INSERT OR IGNORE INTO shows (mal_id, kodi_meta, anime_schedule_route, art, last_updated) '
                'VALUES (?, ?, ?, ?, ?)',
                (mal_id, empty_kodi_meta, '', art_json, last_updated)
            )
        cursor.connection.commit()
