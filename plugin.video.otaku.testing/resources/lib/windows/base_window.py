import pickle
import random
import xbmcgui

from resources.lib.ui import control, database


class BaseWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, xml_file, location, actionArgs=None):
        super().__init__(xml_file, location)

        control.closeBusyDialog()

        # Early exit for skip_intro to avoid unnecessary processing
        if actionArgs is None or actionArgs.get('item_type') == 'skip_intro':
            return

        # Cache mal_id for reuse
        self._mal_id = actionArgs.get('mal_id')
        item_type = actionArgs.get('item_type')

        # Initialize item_information
        if self._mal_id:
            show_data = database.get_show(self._mal_id)
            if show_data:
                self.item_information = pickle.loads(show_data['kodi_meta'])
                show_meta = database.get_show_meta(self._mal_id)
                if show_meta:
                    self.item_information.update(pickle.loads(show_meta.get('art')))
            else:
                self.item_information = {}
        elif item_type == 'playing_next':
            self.item_information = actionArgs
        else:
            self.item_information = {}

        # Set properties efficiently
        self._set_window_properties()

    def _set_window_properties(self):
        """Set window properties in a single method to reduce overhead"""
        # Handle thumb
        thumb = self.item_information.get('thumb')
        if thumb:
            if isinstance(thumb, list):
                thumb = random.choice(thumb)
            self.setProperty('item.art.thumb', thumb)

        # Handle fanart
        fanart = self.item_information.get('fanart')
        if not fanart or control.settingids.fanart_disable:
            fanart = control.OTAKU_FANART
        else:
            if isinstance(fanart, list):
                if control.settingids.fanart_select and self._mal_id:
                    # Get fanart selection using string lists
                    mal_ids = control.getStringList('fanart.mal_ids')
                    fanart_selections = control.getStringList('fanart.selections')
                    mal_id_str = str(self._mal_id)

                    try:
                        index = mal_ids.index(mal_id_str)
                        fanart_select = fanart_selections[index] if index < len(fanart_selections) else ''
                        fanart = fanart_select if fanart_select else random.choice(fanart)
                    except (ValueError, IndexError):
                        fanart = random.choice(fanart)
                else:
                    fanart = random.choice(fanart)

        # Handle clearlogo
        clearlogo = self.item_information.get('clearlogo', control.OTAKU_LOGO2_PATH)
        if isinstance(clearlogo, list):
            clearlogo = control.OTAKU_LOGO2_PATH if control.settingids.clearlogo_disable else random.choice(clearlogo)

        # Set properties in batch
        if self.item_information.get('format') not in ['MOVIE', 'Movie']:
            self.setProperty('item.art.fanart', fanart)

        self.setProperty('item.art.poster', self.item_information.get('poster'))
        self.setProperty('item.art.clearlogo', clearlogo)
        self.setProperty('item.info.title', self.item_information.get('name'))

        # Movie-specific properties
        if self.item_information.get('format') in ['MOVIE', 'Movie']:
            self.setProperty('item.info.plot', self.item_information.get('plot'))
            self.setProperty('item.info.rating', str(self.item_information.get('rating')))
            self.setProperty('item.info.title', self.item_information.get('title_userPreferred'))

    def close(self):
        """Override close to ensure cleanup"""
        # Clear references to prevent memory leaks
        self.item_information = None
        super().close()
