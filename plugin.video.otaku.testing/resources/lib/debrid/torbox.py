import xbmcgui

from resources.lib.ui import source_utils, client, control


class TorBox:
    def __init__(self):
        self.token = control.getSetting('torbox.token')
        self.autodelete = control.getBool('torbox.autodelete')
        self.BaseUrl = "https://api.torbox.app/v1/api"

    def headers(self):
        return {'Authorization': f"Bearer {self.token}"}

    def auth(self):
        self.token = control.input_dialog("Enter API KEY for TorBox:", self.token, xbmcgui.INPUT_ALPHANUM)
        control.setSetting('torbox.token', self.token)
        auth_done = self.status()
        if not auth_done:
            control.ok_dialog(f'{control.ADDON_NAME}: TorBox Auth', "Invalid API KEY!")

    def status(self):
        r = client.get(f'{self.BaseUrl}/user/me', headers=self.headers())
        user_info = r.json()['data'] if r else None
        if user_info:
            control.setSetting('torbox.username', user_info['email'])
            if user_info['plan'] == 0:
                control.setSetting('torbox.auth.status', 'Free')
                control.ok_dialog(f'{control.ADDON_NAME}: TorBox', control.lang(30025))
            elif user_info['plan'] == 1:
                control.setSetting('torbox.auth.status', 'Essential')
            elif user_info['plan'] == 3:
                control.setSetting('torbox.auth.status', 'Standard')
            elif user_info['plan'] == 2:
                control.setSetting('torbox.auth.status', 'Pro')
            control.ok_dialog(control.ADDON_NAME, f'TorBox {control.lang(30024)}')
        return user_info is not None

    def refreshToken(self):
        pass

    def hash_check(self, hash_list):
        hashes = ','.join(hash_list)
        url = f'{self.BaseUrl}/torrents/checkcached'
        params = {
            'hash': hashes,
            'format': 'list'
        }
        r = client.get(url, headers=self.headers(), params=params)
        return r.json()['data'] if r else None

    def addMagnet(self, magnet):
        url = f'{self.BaseUrl}/torrents/createtorrent'
        data = {
            'magnet': magnet
        }
        r = client.post(url, headers=self.headers(), data=data)
        return r.json()['data'] if r else None

    def delete_torrent(self, torrent_id):
        headers = self._get_headers()
        r = client.delete(f'{self.base_url}/torrents/controltorrent', headers=headers, data={'torrent_id': torrent_id, 'operation': 'delete'})
        return r and r.ok

    def list_torrents(self):
        url = f'{self.BaseUrl}/torrents/mylist'
        r = client.get(url, headers=self.headers())
        return r.json()['data'] if r else None

    def get_torrent_info(self, torrent_id):
        url = f'{self.BaseUrl}/torrents/mylist'
        params = {'id': torrent_id, 'bypass_cache': 'true'}
        r = client.get(url, headers=self.headers(), params=params)
        return r.json()['data'] if r else None

    def request_dl_link(self, torrent_id, file_id=-1):
        url = f'{self.BaseUrl}/torrents/requestdl'
        params = {
            'token': self.token,
            'torrent_id': torrent_id
        }
        if file_id >= 0:
            params['file_id'] = file_id
        r = client.get(url, params=params)
        return r.json()['data'] if r else None

    def resolve_single_magnet(self, hash_, magnet, episode, pack_select):
        torrent = self.addMagnet(magnet)
        torrent_id = torrent['torrent_id']
        torrent_info = self.get_torrent_info(torrent_id)
        folder_details = [{'fileId': x['id'], 'path': x['name']} for x in torrent_info['files']]

        if episode:
            selected_file = source_utils.get_best_match('path', folder_details, str(episode), pack_select)
            if selected_file and selected_file['fileId'] is not None:
                stream_link = self.request_dl_link(torrent_id, selected_file['fileId'])
                if self.autodelete:
                    self.delete_torrent(torrent_id)
                return stream_link
        self.delete_torrent(torrent_id)

    def resolve_hoster(self, source):
        return self.request_dl_link(source['folder_id'], source['file']['id'])

    @staticmethod
    def resolve_cloud(source, pack_select):
        if source['hash']:
            best_match = source_utils.get_best_match('short_name', source['hash'], source['episode'], pack_select)
            if not best_match or not best_match['short_name']:
                return
            for f_index, torrent_file in enumerate(source['hash']):
                if torrent_file['short_name'] == best_match['short_name']:
                    return {'folder_id': source['id'], 'file': source['hash'][f_index]}

    def resolve_uncached_source(self, source, runinbackground, runinforground, pack_select):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        if runinforground:
            control.progressDialog.create(heading, "Caching Progress")
        stream_link = None
        magnet = source['magnet']
        torrent = self.addMagnet(magnet)
        torrent_id = torrent['torrent_id']
        torrent_info = self.get_torrent_info(torrent_id)
        status = torrent_info['download_state']

        if runinbackground:
            control.notify(heading, "The source is downloading to your cloud")
            return

        progress = 0
        while status not in ['completed', 'error']:
            if runinforground and (control.progressDialog.iscanceled() or control.wait_for_abort(5)):
                break
            torrent_info = self.get_torrent_info(torrent_id)
            status = torrent_info.get('download_state', 'error')
            progress = torrent_info.get('progress', 0) * 100
            peers = torrent_info.get('peers', 0)
            download_speed = torrent_info.get('download_speed', 0)
            if runinforground:
                f_body = (f"Status: {status}[CR]"
                          f"Progress: {round(progress, 2)} %[CR]"
                          f"Peers: {peers}[CR]"
                          f"Download Speed: {source_utils.get_size(download_speed)}")
                control.progressDialog.update(int(progress), f_body)

        if status == 'completed':
            control.ok_dialog(heading, "This file has been added to your Cloud")
            folder_details = [{'fileId': x['id'], 'path': x['name']} for x in torrent_info['files']]
            selected_file = source_utils.get_best_match('path', folder_details, source['episode_re'], pack_select)
            if selected_file and selected_file['fileId'] is not None:
                stream_link = self.request_dl_link(torrent_id, selected_file['fileId'])
                if self.autodelete:
                    self.delete_torrent(torrent_id)
            else:
                stream_link = self.request_dl_link(torrent_id)
                if self.autodelete:
                    self.delete_torrent(torrent_id)
            if self.autodelete:
                self.delete_torrent(torrent_id)
        else:
            self.delete_torrent(torrent_id)
        if runinforground:
            control.progressDialog.close()
        return stream_link
