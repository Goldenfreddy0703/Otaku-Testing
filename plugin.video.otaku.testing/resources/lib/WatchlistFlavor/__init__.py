from resources.lib.ui import control
from resources.lib.WatchlistFlavor import AniList, Kitsu, MyAnimeList, Simkl  # noQA
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase


class WatchlistFlavor:
    __SELECTED = None

    def __init__(self):
        raise Exception("Static Class should not be created")

    @staticmethod
    def get_enabled_watchlists():
        return [WatchlistFlavor.__instance_flavor(x) for x in control.enabled_watchlists()]

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
        control.setInt('%s.sort' % flavor, 0)
        control.setInt('%s.order' % flavor, 0)
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
        user_id = control.getSetting(f'{name}.userid')
        auth_var = control.getSetting(f'{name}.authvar')
        token = control.getSetting(f'{name}.token')
        refresh = control.getSetting(f'{name}.refresh')
        username = control.getSetting(f'{name}.username')
        password = control.getSetting(f'{name}.password')
        sort = control.getInt(f'{name}.sort')
        order = control.getInt(f'{name}.order')

        flavor_class = WatchlistFlavor.__get_flavor_class(name)
        return flavor_class(auth_var, username, password, user_id, token, refresh, sort, order)

    @staticmethod
    def __set_login(flavor, res):
        if not res:
            return control.ok_dialog('Login', 'Incorrect username or password')
        else:
            mapping = {
                'anilist': 'AniList',
                'kitsu': 'Kitsu',
                'mal': 'MAL',
                'simkl': 'Simkl'
            }
            control.setBool('watchlist.update.enabled', True)
            control.setSetting('watchlist.update.flavor', mapping.get(flavor, flavor.capitalize()))
        for _id, value in list(res.items()):
            setting_name = '%s.%s' % (flavor, _id)
            if _id == 'expiry':
                control.setInt(setting_name, int(value))
            else:
                control.setSetting(setting_name, str(value))
        control.refresh()
        return control.ok_dialog('Login', 'Success')

    @staticmethod
    def watchlist_anime_entry_request(mal_id):
        return WatchlistFlavor.get_update_flavor().get_watchlist_anime_entry(mal_id)

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
