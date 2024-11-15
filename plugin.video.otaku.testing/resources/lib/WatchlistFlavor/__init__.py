from resources.lib.ui import control
from resources.lib.WatchlistFlavor import AniList, Kitsu, MyAnimeList, Simkl
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase


class WatchlistFlavor:
    __LOGIN_KEY = "addon.login"
    __LOGIN_FLAVOR_KEY = "%s.flavor" % __LOGIN_KEY
    __SELECTED = None

    def __init__(self):
        raise Exception("Static Class should not be created")

    @staticmethod
    def get_enabled_watchlists():
        enabled_watchlists = []
        if control.myanimelist_enabled():
            enabled_watchlists.append(WatchlistFlavor.__instance_flavor('mal'))
        if control.kitsu_enabled():
            enabled_watchlists.append(WatchlistFlavor.__instance_flavor('kitsu'))
        if control.anilist_enabled():
            enabled_watchlists.append(WatchlistFlavor.__instance_flavor('anilist'))
        if control.simkl_enabled():
            enabled_watchlists.append(WatchlistFlavor.__instance_flavor('simkl'))
        return enabled_watchlists

    @staticmethod
    def get_enabled_watchlist_list():
        enabled_watchlists = []
        if control.myanimelist_enabled():
            enabled_watchlists.append('mal')
        if control.kitsu_enabled():
            enabled_watchlists.append('kitsu')
        if control.anilist_enabled():
            enabled_watchlists.append('anilist')
        if control.simkl_enabled():
            enabled_watchlists.append('simkl')
        return enabled_watchlists

    @staticmethod
    def get_update_flavor():
        selected = control.watchlist_to_update()
        if not selected:
            return
        if not WatchlistFlavor.__SELECTED:
            WatchlistFlavor.__SELECTED = WatchlistFlavor.__instance_flavor(selected)
        return WatchlistFlavor.__SELECTED

    @staticmethod
    def watchlist_request(name):
        return WatchlistFlavor.__instance_flavor(name).watchlist()

    @staticmethod
    def watchlist_status_request(name, status, next_up, offset=0, page=1):
        return WatchlistFlavor.__instance_flavor(name).get_watchlist_status(status, next_up, offset, page)

    @staticmethod
    def watchlist_anime_entry_request(mal_id):
        return WatchlistFlavor.get_update_flavor().get_watchlist_anime_entry(mal_id)

    @staticmethod
    def login_request(flavor):
        if not WatchlistFlavor.__is_flavor_valid(flavor):
            raise Exception("Invalid flavor %s" % flavor)

        flavor_class = WatchlistFlavor.__instance_flavor(flavor)

        return WatchlistFlavor.__set_login(flavor, flavor_class.login())

    @staticmethod
    def logout_request(flavor):
        control.setSetting('%s.userid' % flavor, '')
        control.setSetting('%s.authvar' % flavor, '')
        control.setSetting('%s.token' % flavor, '')
        control.setSetting('%s.refresh' % flavor, '')
        control.setSetting('%s.username' % flavor, '')
        control.setSetting('%s.password' % flavor, '')
        control.setSetting('%s.sort' % flavor, '')
        control.setSetting('%s.titles' % flavor, '')
        return control.refresh()

    @staticmethod
    def __get_flavor_class(name):
        for flav in WatchlistFlavorBase.__subclasses__():
            if flav.name() == name:
                return flav

    @staticmethod
    def __is_flavor_valid(name):
        return WatchlistFlavor.__get_flavor_class(name) is not None

    @staticmethod
    def __instance_flavor(name):
        user_id = control.getSetting('%s.userid' % name)
        auth_var = control.getSetting('%s.authvar' % name)
        token = control.getSetting('%s.token' % name)
        refresh = control.getSetting('%s.refresh' % name)
        username = control.getSetting('%s.username' % name)
        password = control.getSetting('%s.password' % name)
        sort = control.getSetting('%s.sort' % name)

        flavor_class = WatchlistFlavor.__get_flavor_class(name)
        return flavor_class(auth_var, username, password, user_id, token, refresh, sort)

    @staticmethod
    def __set_login(flavor, res):
        if not res:
            return control.ok_dialog('Login', 'Incorrect username or password')
        for _id, value in list(res.items()):
            control.setSetting('%s.%s' % (flavor, _id), str(value))
        control.refresh()
        return control.ok_dialog('Login', 'Success')

    @staticmethod
    def context_statuses():
        return WatchlistFlavor.get_update_flavor().action_statuses()

    @staticmethod
    def watchlist_update_episode(mal_id, episode):
        return WatchlistFlavor.get_update_flavor().update_num_episodes(mal_id, episode)

    @staticmethod
    def watchlist_set_status(mal_id, status):
        return WatchlistFlavor.get_update_flavor().update_list_status(mal_id, status)

    @staticmethod
    def watchlist_set_score(mal_id, score):
        return WatchlistFlavor.get_update_flavor().update_score(mal_id, score)

    @staticmethod
    def watchlist_delete_anime(mal_id):
        return WatchlistFlavor.get_update_flavor().delete_anime(mal_id)
