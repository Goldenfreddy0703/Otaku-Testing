import pickle
import random
import xbmcgui

from resources.lib.ui import control, database


class BaseWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, xml_file, location, actionArgs=None):
        super().__init__(xml_file, location)

        control.closeBusyDialog()
        if actionArgs is None or (item_type := actionArgs.get('item_type')) == 'skip_intro':
            return

        if mal_id := actionArgs.get('mal_id'):
            self.item_information = pickle.loads(database.get_show(actionArgs['mal_id'])['kodi_meta'])
            show_meta = database.get_show_meta(actionArgs['mal_id'])
            if show_meta:
                self.item_information.update(pickle.loads(show_meta.get('art')))
        elif item_type == 'playing_next':
            self.item_information = actionArgs
        else:
            self.item_information = {}

        if thumb := self.item_information.get('thumb'):
            thumb = random.choice(thumb)
            self.setProperty('item.art.thumb', thumb)

        fanart = self.item_information.get('fanart')
        clearlogo = self.item_information.get('clearlogo', control.OTAKU_LOGO2_PATH)

        if not fanart or control.settingids.fanart_disable:
            fanart = control.OTAKU_FANART
        else:
            if isinstance(fanart, list):
                if control.settingids.fanart_select:
                    # Get fanart selection using string lists
                    mal_ids = control.getStringList('fanart.mal_ids')
                    fanart_selections = control.getStringList('fanart.selections')
                    mal_id_str = str(mal_id)

                    fanart_select = ''
                    try:
                        index = mal_ids.index(mal_id_str)
                        fanart_select = fanart_selections[index] if index < len(fanart_selections) else ''
                    except (ValueError, IndexError):
                        pass

                    fanart = fanart_select if fanart_select else random.choice(fanart)
                else:
                    fanart = random.choice(fanart)
        if isinstance(clearlogo, list):
            clearlogo = control.OTAKU_LOGO2_PATH if control.settingids.clearlogo_disable else random.choice(clearlogo)

        if item_type != 'playing_next':
            self.setProperty('item.art.fanart', fanart)

        self.setProperty('item.art.poster', self.item_information.get('poster'))
        self.setProperty('item.art.clearlogo', clearlogo)
        self.setProperty('item.info.title', self.item_information.get('name'))

        if self.item_information.get('format') in ['MOVIE', 'Movie']:
            self.setProperty('item.info.plot', self.item_information.get('plot'))
            self.setProperty('item.info.rating', str(self.item_information.get('rating')))
            self.setProperty('item.info.title', self.item_information.get('title_userPreferred'))
