import xbmc

from resources.lib.ui import control
from resources.lib.windows.base_window import BaseWindow


class SkipIntro(BaseWindow):
    def __init__(self, xml_file, xml_location, actionArgs=None):
        super().__init__(xml_file, xml_location, actionArgs=actionArgs)
        self.player = xbmc.Player()
        self.total_time = int(self.player.getTotalTime())
        self.playing_file = self.player.getPlayingFile()
        self.current_time = 0
        self.skipintro_end_skip_time = actionArgs['skipintro_end']
        self.skipintro_aniskip = actionArgs['skipintro_aniskip']
        self.closed = False
        self.actioned = None

    def onInit(self):
        self.background_tasks()

    def background_tasks(self):
        """Optimized background task with longer sleep intervals"""
        self.current_time = int(self.player.getTime())
        while self.total_time - self.current_time > 2 and not self.closed and self.playing_file == self.player.getPlayingFile():
            self.current_time = int(self.player.getTime())
            if self.current_time > self.skipintro_end_skip_time:
                self.close()
                break
            xbmc.sleep(1000)  # Check every second
        self.close()

    def doModal(self):
        super(SkipIntro, self).doModal()

    def close(self):
        self.closed = True
        # Cleanup references
        self.player = None
        super(SkipIntro, self).close()

    def onClick(self, controlId):
        self.handle_action(controlId)

    def handle_action(self, controlId):
        if controlId == 3001:
            self.actioned = True
            if self.skipintro_aniskip:
                self.player.seekTime(self.skipintro_end_skip_time)
            else:
                self.player.seekTime(int(self.player.getTime()) + control.getInt('skipintro.time'))
            self.close()

        if controlId == 3002:
            self.actioned = True
            self.close()

    def onAction(self, action):
        actionID = action.getId()

        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            self.close()

        if actionID == 7:
            # ENTER
            self.handle_action(actionID)
