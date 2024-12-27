import json

from resources.lib.ui import client

baseUrl = 'https://api.malsync.moe'


def get_slugs(mal_id, site=''):
    slugs = []
    if site in ['Gogoanime', 'Zoro']:
        response = client.request(f'{baseUrl}/mal/anime/{mal_id}')
        if response:
            resp = json.loads(response)['Sites'].get(site)
            if resp:
                for key in resp.keys():
                    slugs.append(resp[key].get('url'))
    return slugs
