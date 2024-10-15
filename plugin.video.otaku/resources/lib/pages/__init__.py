import threading
import time
import xbmc

from resources.lib.pages import nyaa, animetosho, debrid_cloudfiles, hianime, gogoanime, localfiles
from resources.lib.ui import control, database
from resources.lib.windows.get_sources_window import GetSources
from resources.lib.windows import sort_select


def getSourcesHelper(actionargs):
    sources_window = Sources('get_sources.xml', control.ADDON_PATH, actionargs=actionargs)
    sources = sources_window.doModal()
    del sources_window
    return sources


class Sources(GetSources):
    def __init__(self, xml_file, location, actionargs=None):
        super(Sources, self).__init__(xml_file, location, actionargs)
        self.torrentProviders = ['nyaa', 'animetosho', 'Cloud Inspection']
        self.embedProviders = ['gogo', 'hianime']
        self.localProviders = ['Local Inspection']
        self.remainingProviders = self.embedProviders + self.torrentProviders + self.localProviders

        self.torrents_qual_len = [0, 0, 0, 0, 0]
        self.embeds_qual_len = [0, 0, 0, 0, 0]
        self.return_data = []
        self.progress = 1
        self.threads = []

        self.cloud_files = []
        self.torrentSources = []
        self.torrentCacheSources = []
        self.torrentUnCacheSources = []
        self.embedSources = []
        self.usercloudSources = []
        self.local_files = []

    def getSources(self, args):
        query = args['query']
        mal_id = args['mal_id']
        episode = args['episode']
        status = args['status']
        media_type = args['media_type']
        rescrape = args['rescrape']
        # source_select = args['source_select']
        get_backup = args['get_backup']

        self.setProperty('process_started', 'true')

        # set skipintro times to -1 before scraping
        control.setSetting('hianime.skipintro.start', '-1')
        control.setSetting('hianime.skipintro.end', '-1')

        # set skipoutro times to -1 before scraping
        control.setSetting('hianime.skipoutro.start', '-1')
        control.setSetting('hianime.skipoutro.end', '-1')

        if control.real_debrid_enabled() or control.all_debrid_enabled() or control.debrid_link_enabled() or control.premiumize_enabled():
            t = threading.Thread(target=self.user_cloud_inspection, args=(query, mal_id, episode))
            t.start()
            self.threads.append(t)

            if control.getBool('provider.nyaa'):
                t = threading.Thread(target=self.nyaa_worker, args=(query, mal_id, episode, status, media_type, rescrape))
                t.start()
                self.threads.append(t)
            else:
                self.remainingProviders.remove('nyaa')

            if control.getBool('provider.animetosho'):
                t = threading.Thread(target=self.animetosho_worker, args=(query, mal_id, episode, status, media_type, rescrape))
                t.start()
                self.threads.append(t)
            else:
                self.remainingProviders.remove('animetosho')

        else:
            for provider in self.torrentProviders:
                self.remainingProviders.remove(provider)

        ### local ###
        if control.getBool('provider.localfiles'):
            t = threading.Thread(target=self.user_local_inspection, args=(query, mal_id, episode, rescrape))
            t.start()
            self.threads.append(t)
        else:
            self.remainingProviders.remove('Local Inspection')

        ### embeds ###
        if control.getBool('provider.hianime'):
            t = threading.Thread(target=self.hianime_worker, args=(mal_id, episode, rescrape))
            t.start()
            self.threads.append(t)
        else:
            self.remainingProviders.remove('hianime')

        if control.getBool('provider.gogo'):
            t = threading.Thread(target=self.gogo_worker, args=(mal_id, episode, rescrape, get_backup))
            t.start()
            self.threads.append(t)
        else:
            self.remainingProviders.remove('gogo')

        timeout = 60 if rescrape else int(control.getSetting('general.timeout'))
        start_time = time.perf_counter()
        runtime = 0

        while runtime < timeout:
            if not self.silent:
                self.updateProgress()
                self.update_properties("4K: %s | 1080: %s | 720: %s | SD: %s| EQ: %s" % (
                    control.colorstr(self.torrents_qual_len[0] + self.embeds_qual_len[0]),
                    control.colorstr(self.torrents_qual_len[1] + self.embeds_qual_len[1]),
                    control.colorstr(self.torrents_qual_len[2] + self.embeds_qual_len[2]),
                    control.colorstr(self.torrents_qual_len[3] + self.embeds_qual_len[3]),
                    control.colorstr(self.torrents_qual_len[4] + self.embeds_qual_len[4])
                ))
            xbmc.sleep(500)
        
            if (self.canceled or 
                (control.settingids.terminateoncloud and len(self.cloud_files) > 0) or 
                (control.settingids.terminateonlocal and len(self.local_files) > 0)):
                break
            runtime = time.perf_counter() - start_time
            self.progress = runtime / timeout * 100
        
        if len(self.torrentSources) + len(self.embedSources) + len(self.cloud_files) + len(self.local_files) == 0:
            self.return_data = []
        else:
            self.return_data = self.sortSources(self.torrentSources, self.embedSources, self.cloud_files, self.local_files)
        self.close()
        return self.return_data

    def nyaa_worker(self, query, mal_id, episode, status, media_type, rescrape):
        all_sources = database.get_(nyaa.Sources().get_sources, 8, query, mal_id, episode, status, media_type, rescrape, key='nyaa')
        self.torrentUnCacheSources += all_sources['uncached']
        self.torrentCacheSources += all_sources['cached']
        self.torrentSources += all_sources['cached'] + all_sources['uncached']
        self.remainingProviders.remove('nyaa')

    def animetosho_worker(self, query, mal_id, episode, status, media_type, rescrape):
        all_sources = database.get_(animetosho.Sources().get_sources, 8, query, mal_id, episode, status, media_type, rescrape, key='animetosho')
        self.torrentUnCacheSources += all_sources['uncached']
        self.torrentCacheSources += all_sources['cached']
        self.torrentSources += all_sources['cached'] + all_sources['uncached']
        self.remainingProviders.remove('animetosho')

    ### embeds ###
    def hianime_worker(self, mal_id, episode, rescrape):
        hianime_sources = database.get_(hianime.Sources().get_sources, 8, mal_id, episode, key='hianime')
        self.embedSources += hianime_sources
        for x in hianime_sources:
            if x and x['skip'].get('intro') and x['skip']['intro']['start'] != 0:
                control.setSetting('hianime.skipintro.start', str(x['skip']['intro']['start']))
                control.setSetting('hianime.skipintro.end', str(x['skip']['intro']['end']))
            if x and x['skip'].get('outro') and x['skip']['outro']['start'] != 0:
                control.setSetting('hianime.skipoutro.start', str(x['skip']['outro']['start']))
                control.setSetting('hianime.skipoutro.end', str(x['skip']['outro']['end']))
        self.remainingProviders.remove('hianime')

    def gogo_worker(self, mal_id, episode, rescrape, get_backup):
        self.embedSources += database.get_(gogoanime.Sources().get_sources, 8, mal_id, episode, get_backup, key='gogoanime')
        self.remainingProviders.remove('gogo')

    def user_local_inspection(self, query, mal_id, episode, rescrape):
        self.local_files += localfiles.Sources().get_sources(query, mal_id, episode)
        self.remainingProviders.remove('Local Inspection')

    def user_cloud_inspection(self, query, mal_id, episode):
        debrid = {}
        if control.real_debrid_enabled() and control.getSetting('rd.cloudInspection') == 'true':
            debrid['real_debrid'] = True
        if control.premiumize_enabled() and control.getSetting('premiumize.cloudInspection') == 'true':
            debrid['premiumize'] = True
        if control.all_debrid_enabled() and control.getSetting('alldebrid.cloudInspection') == 'true':
            debrid['all_debrid'] = True
        self.cloud_files += debrid_cloudfiles.Sources().get_sources(debrid, query, episode)
        self.remainingProviders.remove('Cloud Inspection')

    @staticmethod
    def sortSources(torrent_list, embed_list, cloud_files, other_list):
        all_list = torrent_list + embed_list + cloud_files + other_list
        sortedList = [x for x in all_list if control.getInt('general.minResolution') <= x['quality'] <= control.getInt('general.maxResolution')]

        # Filter out sources
        if control.getSetting('general.disable265') == 'true':
            sortedList = [i for i in sortedList if 'HEVC' not in i['info']]
        lang = int(control.getSetting("general.source"))
        if lang != 1:
            langs = [0, 1, 2]
            sortedList = [i for i in sortedList if i['lang'] != langs[lang]]

        # Sort Sources
        SORT_METHODS = sort_select.SORT_METHODS
        sort_options = sort_select.sort_options
        for x in range(len(SORT_METHODS), 0, -1):
            reverse = sort_options[f'sortmethod.{x}.reverse']
            method = SORT_METHODS[int(sort_options[f'sortmethod.{x}'])]
            sortedList = getattr(sort_select, f'sort_by_{method}')(sortedList, not reverse)
        return sortedList

    def updateProgress(self):
        self.torrents_qual_len = [
            len([i for i in self.torrentSources if i['quality'] == 4]),
            len([i for i in self.torrentSources if i['quality'] == 3]),
            len([i for i in self.torrentSources if i['quality'] == 2]),
            len([i for i in self.torrentSources if i['quality'] == 1]),
            len([i for i in self.torrentSources if i['quality'] == 0])
        ]

        self.embeds_qual_len = [
            len([i for i in self.embedSources if i['quality'] == 4]),
            len([i for i in self.embedSources if i['quality'] == 3]),
            len([i for i in self.embedSources if i['quality'] == 2]),
            len([i for i in self.embedSources if i['quality'] == 1]),
            len([i for i in self.embedSources if i['quality'] == 0])
        ]

