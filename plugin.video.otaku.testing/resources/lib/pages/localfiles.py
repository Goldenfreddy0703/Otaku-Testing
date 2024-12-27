import os
import re
import json

from functools import partial
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.ui import source_utils, control, client

PATH = control.getSetting('folder.location')


class Sources(BrowserBase):
    def get_sources(self, query, mal_id, episode):
        filenames = []
        for root, dirs, files in os.walk(PATH):
            for file in files:
                if source_utils.is_file_ext_valid(file):
                    filenames.append(str(os.path.join(root, file).replace(PATH, '')))

        clean_filenames = [re.sub(r'\[.*?]\s*', '', os.path.basename(i).replace(',', '')) for i in filenames]
        filenames_query = ','.join(clean_filenames)
        response = client.request('https://armkai.vercel.app/api/fuzzypacks', params={"dict": filenames_query, "match": query})
        resp = json.loads(response) if response else []
        match_files = []
        for i in resp:
            if episode not in clean_filenames[i]:
                continue
            match_files.append(filenames[i])
        mapfunc = partial(self.process_local_search, episode=episode)
        all_results = list(map(mapfunc, match_files))
        return all_results

    @staticmethod
    def process_local_search(f, episode):
        full_path = os.path.join(PATH, f)
        source = {
            'release_title': os.path.basename(f),
            'hash': os.path.join(PATH, f),
            'provider': 'Local',
            'type': 'local',
            'quality': source_utils.getQuality(f),
            'debrid_provider': 'Local-Debrid',
            'episode_re': episode,
            'size': source_utils.get_size(os.path.getsize(full_path)),
            'seeders': 0,
            'byte_size': os.path.getsize(full_path),
            'info': source_utils.getInfo(f),
            'lang': source_utils.getAudio_lang(f),
            'channel': source_utils.getAudio_channel(f),
            'sub': source_utils.getSubtitle_lang(f)
        }
        return source
