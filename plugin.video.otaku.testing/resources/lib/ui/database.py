import ast
import hashlib
import pickle
import re
import time
import threading
import xbmcvfs

from sqlite3 import OperationalError, dbapi2
from resources.lib.ui import control


def get(function, duration, *args, **kwargs):
    """
    Gets cached value for provided function with optional arguments, or executes and stores the result

    :param function: Function to be executed
    :param duration: Duration of validity of cache in hours
    :param args: Optional arguments for the provided function
    :param kwargs: Optional keyword arguments for the provided function
    """
    key = hash_function(function, args, kwargs)
    if 'key' in kwargs:
        key += kwargs.pop('key')
    cache_result = cache_get(key)
    if cache_result and is_cache_valid(cache_result['date'], duration):
        try:
            return_data = ast.literal_eval(cache_result['value'])
            return return_data
        except:
            import traceback
            control.log(traceback.format_exc(), level='error')
            # Cache is corrupted, invalidate it and fetch fresh data
            control.log("Cache corrupted for key: %s, fetching fresh data" % key, level='warning')
            # Don't return None, fall through to fetch fresh data

    fresh_result = repr(function(*args, **kwargs))
    cache_insert(key, fresh_result)
    if not fresh_result:
        return cache_result if cache_result else fresh_result
    data = ast.literal_eval(fresh_result)
    return data


def remove(function, *args, **kwargs):
    # type: (function, object) -> object or None
    """
    Removes cached value for provided function with optional arguments
    :param function: Function results to be deleted from cache
    :param args: Optional arguments for the provided function
    """
    try:
        key = hash_function(function, args, kwargs)
        cache_remove(key)
        return True

    except Exception:
        return False


def hash_function(function_instance, *args):
    function_name = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))
    return function_name + generate_md5(args)


def generate_md5(*args):
    md5_hash = hashlib.md5()
    [md5_hash.update(str(arg).encode()) for arg in args]
    return str(md5_hash.hexdigest())


def cache_get(key):
    with SQL(control.cacheFile) as cursor:
        cursor.execute('SELECT * FROM cache WHERE key=?', (key,))
        results = cursor.fetchone()
        return results


def cache_insert(key, value):
    now = int(time.time())
    with SQL(control.cacheFile) as cursor:
        cursor.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT, value TEXT, date INTEGER, UNIQUE(key))')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_cache ON cache (key)')
        cursor.execute('REPLACE INTO cache (key, value, date) VALUES (?, ?, ?)', (key, value, now))
        cursor.connection.commit()


def cache_remove(key):
    with SQL(control.cacheFile) as cursor:
        cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
        cursor.connection.commit()
        cursor.close()


def cache_clear():
    with SQL(control.cacheFile) as cursor:
        cursor.execute("DROP TABLE IF EXISTS cache")
        cursor.execute("VACUUM")
        cursor.connection.commit()
        cursor.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT, value TEXT, date INTEGER, UNIQUE(key))')
        control.notify(f'{control.ADDON_NAME}: {control.lang(30030)}', control.lang(30031), time=5000, sound=False)


def is_cache_valid(cached_time, cache_timeout):
    now = int(time.time())
    diff = now - cached_time
    return (cache_timeout * 3600) > diff


def update_show(mal_id, kodi_meta, anime_schedule_route=''):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute('REPLACE INTO shows (mal_id, kodi_meta, anime_schedule_route) VALUES (?, ?, ?)', (mal_id, kodi_meta, anime_schedule_route))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()


def update_show_precomputed(mal_id, kodi_meta, info_dict, cast_list, art_dict, anime_schedule_route=''):
    """
    PERFORMANCE: Store pre-computed metadata for Seren-style list building.

    This function stores ALL metadata needed for creating a ListItem in pre-computed form:
    - info_dict: Complete info dict ready for InfoTagVideo (stored as JSON)
    - cast_list: Complete cast array ready for setCast (stored as JSON)
    - art_dict: Complete art dict ready for setArt (stored as JSON)
    - kodi_meta: Legacy blob format (kept for backwards compatibility)

    When building lists, we can now just SELECT info, cast, art and json.loads() them
    instead of doing expensive merging/processing during list rendering.
    """
    import json
    import datetime

    # Serialize to JSON for storage
    info_json = json.dumps(info_dict) if info_dict else None
    cast_json = json.dumps(cast_list) if cast_list else None
    art_json = json.dumps(art_dict) if art_dict else None
    last_updated = datetime.datetime.now().isoformat()

    with SQL(control.malSyncDB) as cursor:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute(
            'REPLACE INTO shows (mal_id, kodi_meta, anime_schedule_route, info, cast, art, last_updated) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (mal_id, kodi_meta, anime_schedule_route, info_json, cast_json, art_json, last_updated)
        )
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()


def get_show_list(mal_ids):
    """
    PERFORMANCE: Seren-style pre-computed metadata retrieval.
    Single SELECT query to get all pre-computed info, cast, and art as JSON.

    Args:
        mal_ids: List of MAL IDs to retrieve

    Returns:
        Dict mapping mal_id to {info, cast, art, last_updated} with JSON already parsed
    """
    import json

    # DEBUG: Log what we receive
    control.log(f"get_show_list called with {len(mal_ids)} IDs: {mal_ids[:10]}", level='info')

    # Seren-style validation: Filter out None, empty strings, invalid values
    # MUST ensure we only have valid integer IDs
    valid_ids = []
    for mid in mal_ids:
        if mid is not None and mid != '' and str(mid).strip():
            try:
                # Ensure it's a valid integer
                int_val = int(mid)
                valid_ids.append(int_val)  # Store the integer, not the original
            except (ValueError, TypeError):
                control.log(f"Skipping invalid MAL ID: {mid} (type: {type(mid)})", level='warning')

    # DEBUG: Log what we validated
    control.log(f"After validation: {len(valid_ids)} valid IDs: {valid_ids[:10]}", level='info')

    if not valid_ids:
        control.log("No valid IDs after filtering, returning empty dict", level='warning')
        return {}

    try:
        with SQL(control.malSyncDB) as cursor:
            # Build query with placeholders - convert list to tuple for SQL parameter binding
            placeholders = ','.join('?' * len(valid_ids))
            # IMPORTANT: 'cast' is a SQL reserved keyword, must escape with brackets
            query = f"""
                SELECT mal_id, info, [cast], art, last_updated
                FROM shows
                WHERE mal_id IN ({placeholders})
            """
            # DEBUG: Log the query and params
            control.log(f"SQL Query: {query[:100]}...", level='info')
            control.log(f"SQL Params (first 10): {tuple(valid_ids[:10])}", level='info')

            # Execute with tuple conversion for proper parameter binding
            cursor.execute(query, tuple(valid_ids))
            rows = cursor.fetchall()

            # Parse JSON and return as dict keyed by mal_id
            result = {}
            for row in rows:
                mal_id = row['mal_id']
                try:
                    result[mal_id] = {
                        'info': json.loads(row['info']) if row['info'] else None,
                        'cast': json.loads(row['cast']) if row['cast'] else None,
                        'art': json.loads(row['art']) if row['art'] else None,
                        'last_updated': row['last_updated']
                    }
                except (json.JSONDecodeError, TypeError) as e:
                    control.log(f"Error parsing JSON for MAL ID {mal_id}: {e}", level='error')
                    continue

            return result
    except Exception as e:
        control.log(f"Database error in get_show_list with {len(valid_ids)} IDs: {e}", level='error')
        control.log(f"First few IDs: {valid_ids[:5] if valid_ids else 'empty'}", level='error')
        import traceback
        control.log(traceback.format_exc(), level='error')
        return {}


def update_show_meta(mal_id, meta_ids, art):
    meta_ids = pickle.dumps(meta_ids)
    art = pickle.dumps(art)
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute("REPLACE INTO shows_meta (mal_id, meta_ids, art) VALUES (?, ?, ?)", (mal_id, meta_ids, art))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()


def add_mapping_id(mal_id, column, value):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('UPDATE shows SET %s=? WHERE mal_id=?' % column, (value, mal_id))
        cursor.connection.commit()


def update_kodi_meta(mal_id, kodi_meta):
    kodi_meta = pickle.dumps(kodi_meta)
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('UPDATE shows SET kodi_meta=? WHERE mal_id=?', (kodi_meta, mal_id))
        cursor.connection.commit()


def update_show_data(mal_id, data, last_updated=''):
    data = pickle.dumps(data)
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute("REPLACE INTO show_data (mal_id, data, last_updated) VALUES (?, ?, ?)", (mal_id, data, last_updated))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()


def update_episode(mal_id, season, number, update_time, kodi_meta, filler='', anidb_ep_id=''):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('REPLACE INTO episodes (mal_id, season, kodi_meta, last_updated, number, filler, anidb_ep_id) VALUES (?, ?, ?, ?, ?, ?, ?)', (mal_id, season, kodi_meta, update_time, number, filler, anidb_ep_id))
        cursor.connection.commit()


def update_episode_column(mal_id, episode, column, value):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('UPDATE episodes SET %s=? WHERE mal_id=? AND number=?' % column, (value, mal_id, episode))
        cursor.connection.commit()


def get_show_data(mal_id):
    with SQL(control.malSyncDB) as cursor:
        db_query = 'SELECT * FROM show_data WHERE mal_id IN (%s)' % mal_id
        cursor.execute(db_query)
        show_data = cursor.fetchone()
        return show_data


def get_episode_list(mal_id):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('SELECT * FROM episodes WHERE mal_id=?', (mal_id,))
        episodes = cursor.fetchall()
        return episodes


def get_episode(mal_id, episode=None):
    with SQL(control.malSyncDB) as cursor:
        if episode:
            cursor.execute('SELECT * FROM episodes WHERE mal_id=? AND number=?', (mal_id, episode))
        else:
            cursor.execute('SELECT * FROM episodes WHERE mal_id=?', (mal_id,))
        episode = cursor.fetchone()
        return episode


def get_show(mal_id):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('SELECT * FROM shows WHERE mal_id IN (%s)' % mal_id)
        shows = cursor.fetchone()
        return shows


def get_show_meta(mal_id):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('SELECT * FROM shows_meta WHERE mal_id IN (%s)' % mal_id)
        shows = cursor.fetchone()
        return shows


def get_existing_show_meta_ids(mal_ids):
    """
    Batch check which mal_ids already have metadata in the database.
    Returns a set of mal_ids that exist in shows_meta table.

    PERFORMANCE: Replaces 25 individual queries with 1 batch query.
    """
    if not mal_ids:
        return set()

    # Create placeholders for SQL IN clause
    placeholders = ','.join(str(int(mid)) for mid in mal_ids)

    with SQL(control.malSyncDB) as cursor:
        cursor.execute(f'SELECT mal_id FROM shows_meta WHERE mal_id IN ({placeholders})')
        results = cursor.fetchall()
        return {row['mal_id'] for row in results}


def remove_from_database(table, mal_id):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute(f"DELETE FROM {table} WHERE mal_id=?", (mal_id,))
        cursor.connection.commit()


def get_info(api_name):
    with SQL(control.infoDB) as cursor:
        cursor.execute('SELECT * FROM info WHERE api_name=?', (api_name,))
        api_info = cursor.fetchone()
        return api_info


def get_mal_ids(anime_id, send_id):
    with SQL(control.mappingDB) as cursor:
        cursor.execute(f'SELECT * FROM anime WHERE {send_id}=?', (anime_id,))
        mappings = cursor.fetchall()
        return mappings if mappings else []


def get_mappings(anime_id, send_id):
    with SQL(control.mappingDB) as cursor:
        cursor.execute(f'SELECT * FROM anime WHERE {send_id}=?', (anime_id,))
        mappings = cursor.fetchall()
        return mappings[0] if mappings else {}


def get_unique_ids(anime_id, send_id):
    with SQL(control.mappingDB) as cursor:
        cursor.execute(f'SELECT mal_id, mal_dub_id, anilist_id, kitsu_id, anidb_id, simkl_id, thetvdb_id, themoviedb_id, imdb_id, trakt_id FROM anime WHERE {send_id}=?', (anime_id,))
        mappings = cursor.fetchone()
        if mappings:
            mappings_dict = {
                'mal_id': mappings.get('mal_id'),
                'mal_dub_id': mappings.get('mal_dub_id'),
                'anilist_id': mappings.get('anilist_id'),
                'kitsu_id': mappings.get('kitsu_id'),
                'anidb': mappings.get('anidb_id'),
                'simkl': mappings.get('simkl_id'),
                'tvdb': mappings.get('thetvdb_id'),
                'tmdb': mappings.get('themoviedb_id'),
                'imdb': mappings.get('imdb_id'),
                'trakt': mappings.get('trakt_id')
            }
            return mappings_dict
        return {}


def get_show_data_batch(mal_ids):
    """
    Fetch show data, metadata, and mappings for multiple mal_ids in batch queries.
    Returns a dict mapping mal_id -> {show, meta, mappings}

    Performance optimization inspired by Seren/TMDB Helper:
    Instead of 3 queries per item, we do 3 queries total for the entire list.
    For a 25-item list: 75 queries -> 3 queries = 25x reduction in database overhead.
    """
    if not mal_ids:
        return {}

    result = {}

    # Convert to list and create SQL placeholders
    mal_id_list = list(mal_ids)
    placeholders = ','.join(str(int(mid)) for mid in mal_id_list)

    # Batch Query 1: Get all shows at once
    with SQL(control.malSyncDB) as cursor:
        cursor.execute(f'SELECT * FROM shows WHERE mal_id IN ({placeholders})')
        shows = cursor.fetchall()
        for show in shows:
            mal_id = show['mal_id']
            if mal_id not in result:
                result[mal_id] = {}
            result[mal_id]['show'] = show

    # Batch Query 2: Get all show metadata at once
    with SQL(control.malSyncDB) as cursor:
        cursor.execute(f'SELECT * FROM shows_meta WHERE mal_id IN ({placeholders})')
        metas = cursor.fetchall()
        for meta in metas:
            mal_id = meta['mal_id']
            if mal_id not in result:
                result[mal_id] = {}
            result[mal_id]['meta'] = meta

    # Batch Query 3: Get all mappings at once
    with SQL(control.mappingDB) as cursor:
        cursor.execute(f'''
            SELECT mal_id, mal_dub_id, anilist_id, kitsu_id, anidb_id, simkl_id,
                   thetvdb_id, themoviedb_id, imdb_id, trakt_id
            FROM anime WHERE mal_id IN ({placeholders})
        ''')
        mappings = cursor.fetchall()
        for mapping in mappings:
            mal_id = mapping['mal_id']
            if mal_id not in result:
                result[mal_id] = {}

            mappings_dict = {
                'mal_id': mapping.get('mal_id'),
                'mal_dub_id': mapping.get('mal_dub_id'),
                'anilist_id': mapping.get('anilist_id'),
                'kitsu_id': mapping.get('kitsu_id'),
                'anidb': mapping.get('anidb_id'),
                'simkl': mapping.get('simkl_id'),
                'tvdb': mapping.get('thetvdb_id'),
                'tmdb': mapping.get('themoviedb_id'),
                'imdb': mapping.get('imdb_id'),
                'trakt': mapping.get('trakt_id')
            }
            result[mal_id]['mappings'] = mappings_dict

    # Ensure all mal_ids have entries (even if data is missing)
    for mal_id in mal_id_list:
        if mal_id not in result:
            result[mal_id] = {}
        if 'show' not in result[mal_id]:
            result[mal_id]['show'] = None
        if 'meta' not in result[mal_id]:
            result[mal_id]['meta'] = None
        if 'mappings' not in result[mal_id]:
            result[mal_id]['mappings'] = {}

    return result


def ensure_tables_and_indexes(cursor):
    tables = ['anime', 'movie', 'tv_show', 'tv_short', 'special', 'ova', 'ona', 'music']
    for table in tables:
        cursor.execute(f'CREATE TABLE IF NOT EXISTS {table} (value TEXT)')
        cursor.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON {table} (value)')


def getSearchHistory(media_type):
    with SQL(control.searchHistoryDB) as cursor:
        ensure_tables_and_indexes(cursor)
        cursor.execute(f"SELECT * FROM {media_type}")
        history = cursor.fetchall()
        history.reverse()
        history = history[:50]
        filter_ = []
        for i in history:
            if i['value'] not in filter_:
                filter_.append(i['value'])
        return filter_


def addSearchHistory(search_string, media_type):
    with SQL(control.searchHistoryDB) as cursor:
        ensure_tables_and_indexes(cursor)
        cursor.execute(f"REPLACE INTO {media_type} VALUES (?)", (search_string,))
        cursor.connection.commit()


def clearSearchHistory():
    confirmation = control.yesno_dialog(control.ADDON_NAME, "Clear all search history?")
    if not confirmation:
        return
    with SQL(control.searchHistoryDB) as cursor:
        tables = ['anime', 'movie', 'tv_show', 'tv_short', 'special', 'ova', 'ona', 'music']
        for table in tables:
            cursor.execute(f'DROP TABLE IF EXISTS {table}')
        cursor.execute("VACUUM")
        cursor.connection.commit()
        control.refresh()
        control.notify(control.ADDON_NAME, "Search History has been cleared", time=5000)


def clearSearchCatagory(media_type):
    confirmation = control.yesno_dialog(control.ADDON_NAME, "Clear search history?")
    if not confirmation:
        return
    with SQL(control.searchHistoryDB) as cursor:
        cursor.execute(f'DROP TABLE IF EXISTS {media_type}')
        cursor.execute(f'CREATE TABLE IF NOT EXISTS {media_type} (value TEXT)')
        cursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON {media_type} (value)")
        cursor.connection.commit()
        control.refresh()
        control.notify(control.ADDON_NAME, "Search History has been cleared", time=5000)


def remove_search(table, value):
    norm_value = value.strip()
    with SQL(control.searchHistoryDB) as cursor:
        cursor.execute(f'DELETE FROM {table} WHERE value=?', (norm_value,))
        deleted = cursor.rowcount
        cursor.connection.commit()
        control.refresh()
        if deleted == 0:
            control.notify(control.ADDON_NAME, f"Search item not found: '{norm_value}'", time=3000)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class SQL:
    def __init__(self, path, timeout=60):
        self.lock = threading.Lock()
        self.path = path
        self.timeout = timeout

    def __enter__(self):
        self.lock.acquire()
        xbmcvfs.mkdir(control.dataPath)
        conn = dbapi2.connect(self.path, timeout=self.timeout)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA FOREIGN_KEYS=1")
        self.cursor = conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        if self.lock.locked():
            self.lock.release()
        if exc_type:
            import traceback
            control.log('database error', level='error')
            control.log(f"{''.join(traceback.format_exception(exc_type, exc_val, exc_tb))}", level='error')
        if exc_type is OperationalError:
            import traceback
            control.log('database error', level='error')
            control.log(f"{''.join(traceback.format_exception(exc_type, exc_val, exc_tb))}", level='error')
            return True
