import re
import threading
import json

from resources.lib.ui import source_utils, client
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.debrid import real_debrid, premiumize, all_debrid, torbox


class Sources(BrowserBase):
    def __init__(self):
        self.cloud_files = []
        self.threads = []

    def get_sources(self, debrid, query, episode):
        if debrid.get('rd'):
            t = threading.Thread(target=self.rd_cloud_inspection, args=(query, episode,))
            t.start()
            self.threads.append(t)
        if debrid.get('premiumize'):
            t = threading.Thread(target=self.premiumize_cloud_inspection, args=(query, episode,))
            t.start()
            self.threads.append(t)
        if debrid.get('alldebrid'):
            t = threading.Thread(target=self.alldebrid_cloud_inspection, args=(query, episode,))
            t.start()
            self.threads.append(t)
        if debrid.get('torbox'):
            t = threading.Thread(target=self.torbox_cloud_inspection, args=(query, episode,))
            t.start()
            self.threads.append(t)
        for i in self.threads:
            i.join()
        return self.cloud_files

    def rd_cloud_inspection(self, query, episode):
        api = real_debrid.RealDebrid()
        torrents = api.list_torrents()
        filenames = [re.sub(r'\[.*?]\s*', '', i['filename'].replace(',', '')) for i in torrents]
        filenames_query = ','.join(filenames)
        response = client.request('https://armkai.vercel.app/api/fuzzypacks', params={"dict": filenames_query, "match": query})
        resp = json.loads(response) if response else []

        for i in resp:
            torrent = torrents[i]
            filename = re.sub(r'\[.*?]', '', torrent['filename']).lower()
            if source_utils.is_file_ext_valid(filename) and episode not in filename:
                continue
            torrent_info = api.torrentInfo(torrent['id'])
            torrent_files = [selected for selected in torrent_info['files'] if selected['selected'] == 1]

            if len(torrent_files) > 1 and len(torrent_info['links']) == 1:
                continue

            if not any(source_utils.is_file_ext_valid(tor_file['path'].lower()) for tor_file in torrent_files):
                continue

            self.cloud_files.append(
                {
                    'quality': source_utils.getQuality(torrent['filename']),
                    'lang': source_utils.getAudio_lang(torrent['filename']),
                    'channel': source_utils.getAudio_channel(torrent['filename']),
                    'sub': source_utils.getSubtitle_lang(torrent['filename']),
                    'hash': torrent_info['links'],
                    'provider': 'Cloud',
                    'type': 'cloud',
                    'release_title': torrent['filename'],
                    'info': source_utils.getInfo(torrent['filename']),
                    'debrid_provider': 'Real-Debrid',
                    'size': source_utils.get_size(torrent['bytes']),
                    'seeders': 0,
                    'byte_size': torrent['bytes'],
                    'torrent': torrent,
                    'torrent_files': torrent_files,
                    'torrent_info': torrent_info,
                    'episode': episode
                }
            )

    def premiumize_cloud_inspection(self, query, episode):
        query1, query2 = query.replace('(', '').replace(')', '').rsplit('|', 1)
        cloud_items = premiumize.Premiumize().search_folder(query1)
        cloud_items += premiumize.Premiumize().search_folder(query2)
        unique_cloud_items = []
        [unique_cloud_items.append(i) for i in cloud_items if i not in unique_cloud_items]
        for torrent in unique_cloud_items:
            filename = re.sub(r'\[.*?]', '', torrent['name']).lower()

            if torrent['type'] == 'file':
                if source_utils.is_file_ext_valid(filename) and episode.zfill(2) not in filename.rsplit('-', 1)[1]:
                    continue

            self.cloud_files.append(
                {
                    'id': torrent['id'],
                    'torrent_type': torrent['type'],
                    'quality': source_utils.getQuality(torrent['name']),
                    'lang': source_utils.getAudio_lang(torrent['name']),
                    'channel': source_utils.getAudio_channel(torrent['name']),
                    'sub': source_utils.getSubtitle_lang(torrent['name']),
                    'hash': torrent.get('link', ''),
                    'provider': 'Cloud',
                    'type': 'cloud',
                    'release_title': torrent['name'],
                    'info': source_utils.getInfo(torrent['name']),
                    'debrid_provider': 'Premiumize',
                    'size': source_utils.get_size(int(torrent.get('size', 0))),
                    'seeders': 0,
                    'byte_size': int(torrent.get('size', 0)),
                    'episode': episode
                }
            )

    def torbox_cloud_inspection(self, query, episode):
        cloud_items = torbox.TorBox().list_torrents()
        filenames = [re.sub(r'\[.*?]\s*', '', i['name'].replace(',', '')) for i in cloud_items]
        filenames_query = ','.join(filenames)
        response = client.request('https://armkai.vercel.app/api/fuzzypacks', params={"dict": filenames_query, "match": query})
        resp = json.loads(response) if response else []
        for i in resp:
            torrent = cloud_items[i]
            filename = re.sub(r'\[.*?]', '', torrent['name']).lower()
            if not torrent['cached'] or not torrent['download_finished'] or len(torrent['files']) < 1 or episode not in filename:
                continue
            if not any(source_utils.is_file_ext_valid(tor_file['short_name'].lower()) for tor_file in torrent['files']):
                continue

            self.cloud_files.append(
                {
                    'id': torrent['id'],
                    'quality': source_utils.getQuality(torrent['name']),
                    'lang': source_utils.getAudio_lang(torrent['name']),
                    'channel': source_utils.getAudio_channel(torrent['name']),
                    'sub': source_utils.getSubtitle_lang(torrent['name']),
                    'hash': torrent['files'],
                    'provider': 'Cloud',
                    'type': 'cloud',
                    'release_title': torrent['name'],
                    'info': source_utils.getInfo(torrent['name']),
                    'debrid_provider': 'TorBox',
                    'size': source_utils.get_size(torrent['size']),
                    'seeders': 0,
                    'byte_size': torrent['size'],
                    'torrent': torrent,
                    'episode': episode
                }
            )

    def alldebrid_cloud_inspection(self, query, episode):
        api = all_debrid.AllDebrid()
        torrents = api.list_torrents()['links']
        filenames = [re.sub(r'\[.*?]\s*', '', i['filename'].replace(',', '')) for i in torrents]
        filenames_query = ','.join(filenames)
        response = client.request('https://armkai.vercel.app/api/fuzzypacks', params={"dict": filenames_query, "match": query})
        resp = json.loads(response) if response else []
        for i in resp:
            torrent = torrents[i]
            filename = re.sub(r'\[.*?]', '', torrent['filename']).lower()
            if source_utils.is_file_ext_valid(filename) and episode not in filename:
                continue

            torrent_info = api.link_info(torrent['link'])
            torrent_files = torrent_info['infos']

            if len(torrent_files) > 1 and len(torrent_info['links']) == 1:
                continue

            if not any(source_utils.is_file_ext_valid(tor_file['filename'].lower()) for tor_file in torrent_files):
                continue

            url = api.resolve_hoster(torrent['link'])
            self.cloud_files.append(
                {
                    'quality': source_utils.getQuality(torrent['filename']),
                    'lang': source_utils.getAudio_lang(torrent['filename']),
                    'channel': source_utils.getAudio_channel(torrent['filename']),
                    'sub': source_utils.getSubtitle_lang(torrent['filename']),
                    'hash': url,
                    'provider': 'Cloud',
                    'type': 'cloud',
                    'release_title': torrent['filename'],
                    'info': source_utils.getInfo(torrent['filename']),
                    'debrid_provider': 'Alldebrid',
                    'size': source_utils.get_size(torrent['size']),
                    'seeders': 0,
                    'byte_size': int(torrent['size']),
                    'episode': episode
                }
            )