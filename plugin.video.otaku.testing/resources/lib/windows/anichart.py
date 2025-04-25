# -*- coding: utf-8 -*-

from resources.lib.ui import control
from resources.lib.windows.anichart_window import BaseWindow
from resources.lib import OtakuBrowser, WatchlistIntegration

BROWSER = OtakuBrowser.BROWSER


class Anichart(BaseWindow):

    def __init__(self, xml_file, location, get_anime=None, anime_items=None):
        super().__init__(xml_file, location)
        self.get_anime = get_anime
        self.anime_items = anime_items
        self.position = -1
        self.display_list = None
        self.last_action = 0
        control.closeBusyDialog()
        self.anime_item = None

    def onInit(self):
        self.display_list = self.getControl(1000)
        menu_items = []

        for idx, i in enumerate(self.anime_items):
            if not i:
                continue

            menu_item = control.menuItem(label='%s' % i['release_title'])
            for info in list(i.keys()):
                try:
                    value = i[info]
                    if isinstance(value, list):
                        value = [str(k) for k in value]
                        value = ' '.join(sorted(value))
                    menu_item.setProperty(info, str(value).replace('_', ' '))
                except UnicodeEncodeError:
                    menu_item.setProperty(info, i[info])

            menu_items.append(menu_item)
            self.display_list.addItem(menu_item)

        self.setFocusId(1000)

    def doModal(self):
        super().doModal()
        return self.anime_item

    def onClick(self, controlId):

        if controlId == 1000:
            self.handle_action(7)

    def handle_action(self, actionID):
        if actionID == 7 and self.getFocusId() == 1000:
            self.position = self.display_list.getSelectedPosition()
            self.resolve_item()

        if actionID == 92 or id == 10:
            self.anime_item = False
            self.close()

    def onAction(self, action):
        actionID = action.getId()

        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            self.close()

        if actionID == 7:
            # ENTER / BACKSPACE / ESCAPE
            self.handle_action(actionID)

        if actionID == 117:
            context_menu_options = []
            if control.getBool('context.otaku.testing.findrecommendations'):
                context_menu_options.append("Find Recommendations")
            if control.getBool('context.otaku.testing.findrelations'):
                context_menu_options.append("Find Relations")
            if control.getBool('context.otaku.testing.getwatchorder'):
                context_menu_options.append("Get Watch Order")
            if control.getBool('context.otaku.testing.watchlist'):
                context_menu_options.append("WatchList Manager")

            context = control.context_menu(context_menu_options)
            self.position = self.display_list.getSelectedPosition()
            anime = self.anime_items[self.position]['id']
            page = 1

            if context == 0 and control.getBool('context.otaku.testing.findrecommendations'):  # Find Recommendations
                control.draw_items(BROWSER.get_recommendations(anime, page), 'tvshows')
                self.close()
            elif context == 1 and control.getBool('context.otaku.testing.findrelations'):  # Find Relations
                control.draw_items(BROWSER.get_relations(anime), 'tvshows')
                self.close()
            elif context == 2 and control.getBool('context.otaku.testing.getwatchorder'):  # Get Watch Order
                control.draw_items(BROWSER.get_watch_order(anime), 'tvshows')
                self.close()
            elif context == 3 and control.getBool('context.otaku.testing.watchlist'):  # WatchList Manager
                payload = f"some_path/{anime}/0"  # Construct the payload, replace 'some/path' with actual path if needed
                params = {}  # Construct the params if needed
                WatchlistIntegration.CONTEXT_MENU(payload, params)

    def resolve_item(self):
        anime = self.anime_items[self.position]['id']
        self.anime_item = self.get_anime(anime)

        if self.anime_item is None:
            return
        else:
            self.close()
