import json

from resources.lib.ui import client


def get_skip_times(mal_id, episodenum, skip_type):
    # skip_types = op, recap, mixed-ed, mixed-op, ed
    url = 'https://api.aniskip.com/v2/skip-times/%s/%d' % (mal_id, episodenum)
    params = {
        'types': skip_type,
        'episodeLength': 0
    }
    response = client.request(url, params=params)
    if response:
        res = json.loads(response)
        return res
