import json
import time
from resources.lib.ui import client, control, source_utils, database


class DebridLink:
    def __init__(self):
        api_info = database.get_info('Debrid-Link')
        self.ClientID = api_info['client_id']
        self.USER_AGENT = 'Otaku'
        self.token = control.getSetting('debridlink.token')
        self.refresh = control.getSetting('debridlink.refresh')
        self.autodelete = control.getBool('debridlink.autodelete')
        self.api_url = "https://debrid-link.fr/api/v2"
        self.cache_check_results = {}
        self.DeviceCode = ''
        self.OauthTimeStep = 0
        self.OauthTimeout = 0
        self.OauthTotalTimeout = 0

    def headers(self):
        return {'User-Agent': self.USER_AGENT, 'Authorization': f"Bearer {self.token}"}

    def auth_loop(self):
        if control.progressDialog.iscanceled():
            control.progressDialog.close()
            self.OauthTimeout = 0
            return False
        control.progressDialog.update(int(self.OauthTimeout / self.OauthTotalTimeout * 100))
        url = f"{self.api_url[:-3]}/oauth/token"
        data = {
            'client_id': self.ClientID,
            'code': self.DeviceCode,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
        }
        r = client.request(url, post=data, headers={'User-Agent': self.USER_AGENT})
        if r:
            response = json.loads(r)
            control.progressDialog.close()
            self.token = response.get('access_token')
            self.refresh = response.get('refresh_token')
            control.setSetting('debridlink.token', self.token)
            control.setSetting('debridlink.refresh', self.refresh)
            control.setInt('debridlink.expiry', int(time.time()) + int(response['expires_in']))
            return True

    def auth(self):
        url = '{0}/oauth/device/code'.format(self.api_url[:-3])
        data = {'client_id': self.ClientID, 'scope': 'get.post.delete.seedbox get.account'}
        r = client.request(url, post=data, headers={'User-Agent': self.USER_AGENT})
        if r:
            resp = json.loads(r)
            self.OauthTotalTimeout = self.OauthTimeout = resp['expires_in']
            self.OauthTimeStep = resp['interval']
            self.DeviceCode = resp['device_code']

            copied = control.copy2clip(resp.get('user_code'))
            display_dialog = (
                f"{control.lang(30021).format(control.colorstr(resp['verification_url']))}[CR]"
                f"{control.lang(30022).format(control.colorstr(resp['user_code']))}"
            )
            if copied:
                display_dialog = f"{display_dialog}[CR]{control.lang(30023)}"
            control.progressDialog.create(f'{control.ADDON_NAME}: Debrid-Link Auth', display_dialog)
            control.progressDialog.update(100)
            auth_done = False
            while not auth_done and self.OauthTimeout > 0:
                self.OauthTimeout -= self.OauthTimeStep
                control.sleep(self.OauthTimeStep * 1000)
                auth_done = self.auth_loop()
            if auth_done:
                self.status()

    def status(self):
        url = f"{self.api_url[:-3]}/account/infos"
        response = client.request(url, headers=self.headers())
        response = json.loads(response)
        username = response['value']['pseudo']
        premium = response['value']['premiumLeft'] > 0
        control.setSetting('debridlink.username', username)
        control.ok_dialog(control.ADDON_NAME, f'Debrid-Link {control.lang(30024)}')
        control.setBool('show.uncached', True)
        control.setBool('uncached.autoruninforground', False)
        control.setBool('uncached.autoruninbackground', False)
        control.setBool('uncached.autoskipuncached', True)
        if not premium:
            control.setSetting('debridlink.auth.status', 'Expired')
            control.ok_dialog(f'{control.ADDON_NAME}: Debrid-Link', control.lang(30025))
        else:
            control.setSetting('debridlink.auth.status', 'Premium')

    def refreshToken(self):
        postData = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh,
            'client_id': self.ClientID
        }
        url = f"{self.api_url[:-3]}/oauth/token"
        response = client.request(url, post=postData, headers={'User-Agent': self.USER_AGENT})
        response = json.loads(response)
        if response.get('access_token'):
            self.token = response['access_token']
            control.setSetting('debridlink.token', self.token)
            control.setInt('debridlink.expiry', int(time.time()) + response['expires_in'])

    def addMagnet(self, magnet):
        postData = {
            'url': magnet,
            'async': 'true'
        }
        url = f"{self.api_url}/seedbox/add"
        r = client.request(url, post=postData, headers=self.headers())
        return json.loads(r).get('value') if r else None

    def resolve_single_magnet(self, hash_, magnet, episode, pack_select):
        files = self.addMagnet(magnet)['files']
        folder_details = [{'link': x['downloadUrl'], 'path': x['name']} for x in files]
        if episode:
            selected_file = source_utils.get_best_match('path', folder_details, episode, pack_select)
            if selected_file is not None:
                return selected_file['link']

        sources = [(item.get('size'), item.get('downloadUrl'))for item in files if any(item.get('name').lower().endswith(x) for x in ['avi', 'mp4', 'mkv'])]

        selected_file = max(sources)[1]
        if selected_file is None:
            return
        return selected_file

    @staticmethod
    def resolve_cloud(source, pack_select):
        pass
