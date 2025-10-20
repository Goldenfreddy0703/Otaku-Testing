from resources.lib.ui import client, database

api_info = database.get_info('TVDB')
api_key = api_info['api_key']
baseUrl = "https://api4.thetvdb.com/v4"
_token_cache = {'token': None, 'timestamp': 0}


def _get_auth_token():
    """Get or refresh TVDB API token"""
    import time
    # Token valid for 30 days, but refresh after 7 days to be safe
    if _token_cache['token'] and (time.time() - _token_cache['timestamp']) < 604800:
        return _token_cache['token']

    # Get new token
    headers = {'Content-Type': 'application/json'}
    data = {'apikey': api_key}
    response = client.post(f'{baseUrl}/login', json=data, headers=headers)

    if response:
        res = response.json()
        token = res.get('data', {}).get('token')
        if token:
            _token_cache['token'] = token
            _token_cache['timestamp'] = time.time()
            return token
    return None


def getArt(meta_ids, mtype):
    art = {}
    tvdb_id = meta_ids.get('thetvdb_id')

    if not tvdb_id:
        return art

    token = _get_auth_token()
    if not token:
        return art

    headers = {'Authorization': f'Bearer {token}'}

    # TVDB uses 'series' for TV shows and 'movies' for movies
    endpoint_type = 'series' if mtype != 'movies' else 'movies'

    # Get artwork for the series/movie
    response = client.get(f'{baseUrl}/{endpoint_type}/{tvdb_id}/artworks', headers=headers)
    res = response.json() if response else {}

    if res and res.get('data'):
        artworks = res['data']

        # Collect fanart (backgrounds)
        backgrounds = [item for item in artworks if item.get('type') == 3]  # Type 3 is backgrounds
        if backgrounds:
            items = [item.get('image') for item in backgrounds if item.get('image')]
            if items:
                # Prepend TVDB image base URL
                art['fanart'] = [f"https://artworks.thetvdb.com{img}" for img in items]

        # Collect thumbnails
        banners = [item for item in artworks if item.get('type') in [1, 2]]  # Type 1 is series banners, 2 is season banners
        if banners:
            items = [item.get('image') for item in banners if item.get('image')]
            if items:
                art['thumb'] = [f"https://artworks.thetvdb.com{img}" for img in items]

        # Collect clearlogo
        clearlogos = [item for item in artworks if item.get('type') == 22]  # Type 22 is clearlogo
        if clearlogos:
            items = [item.get('image') for item in clearlogos if item.get('image')]
            if items:
                art['clearlogo'] = [f"https://artworks.thetvdb.com{img}" for img in items]

        # Collect clearart
        cleararts = [item for item in artworks if item.get('type') == 23]  # Type 23 is clearart
        if cleararts:
            items = [item.get('image') for item in cleararts if item.get('image')]
            if items:
                art['clearart'] = [f"https://artworks.thetvdb.com{img}" for img in items]

    return art
