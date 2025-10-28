from resources.lib.ui import client, control, database

api_info = database.get_info('TVDB')
api_key = api_info.get('api_key') if api_info else None
baseUrl = "https://api4.thetvdb.com/v4"
lang = ['eng', 'jpn']
language = ["jpn", 'eng'][control.getInt("titlelanguage")]


def get_auth_token():
    """Get authentication token for TVDB API v4"""
    if not api_key:
        return None

    headers = {'Content-Type': 'application/json'}
    data = {'apikey': api_key}
    response = client.post(f'{baseUrl}/login', json_data=data, headers=headers)

    if response:
        res = response.json()
        return res.get('data', {}).get('token')
    return None


def getArt(meta_ids, mtype):
    """Get artwork from TVDB API v4"""
    art = {}
    tvdb_id = meta_ids.get('thetvdb_id')

    if not tvdb_id:
        return art

    # Get authentication token
    token = get_auth_token()
    if not token:
        control.log("TVDB: Failed to authenticate")
        return art

    headers = {'Authorization': f'Bearer {token}'}

    # TVDB v4 uses different endpoints for series and movies
    if mtype == 'movies':
        # For movies, use the movies endpoint
        response = client.get(f'{baseUrl}/movies/{tvdb_id}/extended', headers=headers)
    else:
        # For TV shows, use the series endpoint with artworks
        response = client.get(f'{baseUrl}/series/{tvdb_id}/extended', headers=headers)

    if not response:
        return art

    res = response.json()
    data = res.get('data', {})

    if not data:
        return art

    # Process artworks
    artworks = data.get('artworks', [])

    if artworks:
        fanart_images = []
        thumb_images = []
        clearart_images = []
        clearlogo_images = []

        for artwork in artworks:
            artwork_type = artwork.get('type')
            image_url = artwork.get('image')
            artwork_lang = artwork.get('language')

            if not image_url:
                continue

            # Prepend base URL if needed
            if not image_url.startswith('http'):
                image_url = f'https://artworks.thetvdb.com{image_url}'

            # Fanart/Background
            if artwork_type in [3, 15]:  # 3=Series Background, 15=Movie Background
                if artwork_lang in lang or not artwork_lang:
                    fanart_images.append(image_url)

            # Thumbnails/Posters
            elif artwork_type in [2, 14]:  # 2=Series Poster, 14=Movie Poster
                if artwork_lang in lang or not artwork_lang:
                    thumb_images.append(image_url)

            # Clear Art
            elif artwork_type in [22, 23]:  # 22=Clear Art, 23=HD Clear Art
                if artwork_lang in lang or not artwork_lang:
                    clearart_images.append(image_url)

            # Clear Logo (language-specific)
            elif artwork_type in [5, 6]:  # 5=Clear Logo, 6=HD Clear Logo
                clearlogo_images.append({
                    'url': image_url,
                    'lang': artwork_lang
                })

        # Add to art dict
        if fanart_images:
            art['fanart'] = fanart_images
        if thumb_images:
            art['thumb'] = thumb_images
        if clearart_images:
            art['clearart'] = clearart_images

        # Process clearlogo with language preference
        if clearlogo_images:
            logos = []
            # Try to get logo in preferred language
            try:
                logos.append(next(x['url'] for x in clearlogo_images if x['lang'] == language))
            except StopIteration:
                pass

            # If no preferred language logo, try any language in our list
            if not logos:
                try:
                    logos.append(next(x['url'] for x in clearlogo_images if x['lang'] in lang))
                except StopIteration:
                    pass

            # If still no logo, take first available
            if not logos and clearlogo_images:
                try:
                    logos.append(clearlogo_images[0]['url'])
                except (IndexError, KeyError):
                    pass

            if logos:
                art['clearlogo'] = logos

    return art
