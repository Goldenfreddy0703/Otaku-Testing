from resources.lib.ui import control
from sqlite3 import version
from resources.lib.ui.database import SQL

sqlite_version = version


class SyncDatabase:
    def __init__(self):
        self.activites = None

        self.build_sync_activities()
        self.build_show_table()
        self.build_showmeta_table()
        self.build_episode_table()
        self.build_show_data_table()

        # PERFORMANCE: Migrate to Seren-style pre-computed metadata
        self.migrate_to_precomputed_metadata()

        # If you make changes to the required meta in any indexer that is cached in this database
        # You will need to update the below version number to match the new addon version
        # This will ensure that the metadata required for operations is available
        # You may also update this version number to force a rebuild of the database after updating Otaku
        self.last_meta_update = '1.0.9'
        self.refresh_activites()
        self.check_database_version()

    def refresh_activites(self):
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('SELECT * FROM activities WHERE sync_id=1')
            self.activites = cursor.fetchone()

    def set_base_activites(self):
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('INSERT INTO activities(sync_id, otaku_version) VALUES(1, ?)', (self.last_meta_update,))
            cursor.connection.commit()

    def check_database_version(self):
        # import xbmcvfs
        if not self.activites or self.activites.get('otaku_version') != self.last_meta_update:
            # xbmcvfs.delete(control.sort_options_json)
            # xbmcvfs.delete(control.searchHistoryDB)
            first_time = control.getBool('first_time')
            current_version = control.getSetting('version')
            target_version = '0.5.43'

            # Convert version strings to tuples of integers for comparison
            try:
                current_parts = tuple(map(int, current_version.split('.')))
                target_parts = tuple(map(int, target_version.split('.')))

                if current_parts <= target_parts:
                    self.migration_process()
            except (ValueError, AttributeError):
                # Fallback to exact comparison if version format is invalid
                if current_version == target_version:
                    self.migration_process()

            if first_time:
                control.setInt('showchangelog', 1)
                # Ask the user if they would like to go throught the setup wizard
                # Here the button labels are:
                # Button 0: "Yes"   | Button 1: "No"
                choice = control.yesno_dialog(
                    control.ADDON_NAME + ' - ' + control.lang(30417),
                    "Welcome to Otaku!!!\nWould you like to go through the setup wizard?",
                    "No", "Yes",
                )

                # Yes selected
                if choice == 1:
                    control.setBool('first_time', False)
                    control.execute('RunPlugin(plugin://plugin.video.otaku.testing/setup_wizard)')

                # No selected
                elif choice == 0:
                    control.setBool('first_time', False)

            self.re_build_database(True)

            # Clear last_watched setting
            control.setSetting('addon.last_watched', '')

            # Update menu configurations with last_watched and watch_history items
            self._update_menu_config('menu.mainmenu.config', 'last_watched', 'watch_history')
            self._update_menu_config('movie.mainmenu.config', 'last_watched_movie', 'watch_history_movie')
            self._update_menu_config('tv_show.mainmenu.config', 'last_watched_tv_show', 'watch_history_tv_show')
            self._update_menu_config('tv_short.mainmenu.config', 'last_watched_tv_short', 'watch_history_tv_short')
            self._update_menu_config('special.mainmenu.config', 'last_watched_special', 'watch_history_special')
            self._update_menu_config('ova.mainmenu.config', 'last_watched_ova', 'watch_history_ova')
            self._update_menu_config('ona.mainmenu.config', 'last_watched_ona', 'watch_history_ona')
            self._update_menu_config('music.mainmenu.config', 'last_watched_music', 'watch_history_music')

    def _update_menu_config(self, config_key, last_watched_item, watch_history_item):
        """Helper method to update menu configurations with last_watched and watch_history items"""
        menu = control.getStringList(config_key)
        if menu:
            # Add last_watched item if not already in the list
            if last_watched_item not in menu:
                menu.insert(0, last_watched_item)

            # Add watch_history item if not already in the list
            if watch_history_item not in menu:
                # Insert watch_history after last_watched if last_watched exists
                if last_watched_item in menu:
                    insert_index = menu.index(last_watched_item) + 1
                    menu.insert(insert_index, watch_history_item)
                else:
                    menu.insert(0, watch_history_item)
            control.setStringList(config_key, menu)

    @staticmethod
    def build_show_table():
        with SQL(control.malSyncDB) as cursor:
            # Check if table exists and has old schema
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='shows'")
            existing_schema = cursor.fetchone()

            # fetchone() returns a dict due to dict_factory, access with 'sql' key
            if existing_schema and 'info TEXT' not in existing_schema.get('sql', ''):
                # Old schema exists - migrate to new schema
                control.log('Migrating shows table to new Seren-style schema...', level='info')

                # Add new columns
                try:
                    cursor.execute('ALTER TABLE shows ADD COLUMN info TEXT')
                except:
                    pass  # Column might already exist
                try:
                    cursor.execute('ALTER TABLE shows ADD COLUMN cast TEXT')
                except:
                    pass
                try:
                    cursor.execute('ALTER TABLE shows ADD COLUMN art TEXT')
                except:
                    pass
                try:
                    cursor.execute('ALTER TABLE shows ADD COLUMN last_updated TEXT')
                except:
                    pass

                control.log('Shows table migration complete!', level='info')
            elif not existing_schema:
                # Table doesn't exist - create with new schema
                cursor.execute('CREATE TABLE IF NOT EXISTS shows (mal_id INTEGER PRIMARY KEY, '
                               'anilist_id INTEGER,'
                               'simkl_id INTEGER,'
                               'kitsu_id INTEGER,'
                               'kodi_meta BLOB NOT NULL, '
                               'anime_schedule_route TEXT NOT NULL, '
                               'info TEXT, '
                               'cast TEXT, '
                               'art TEXT, '
                               'last_updated TEXT, '
                               'UNIQUE(mal_id))')

            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_shows ON "shows" (mal_id ASC )')
            cursor.connection.commit()

    @staticmethod
    def build_showmeta_table():
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS shows_meta (mal_id INTEGER PRIMARY KEY, '
                           'meta_ids BLOB,'
                           'art BLOB, '
                           'UNIQUE(mal_id))')
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_shows_meta ON "shows_meta" (mal_id ASC )')
            cursor.connection.commit()

    @staticmethod
    def build_show_data_table():
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS show_data (mal_id INTEGER PRIMARY KEY, '
                           'data BLOB NOT NULL, '
                           'last_updated TEXT NOT NULL, '
                           'UNIQUE(mal_id))')
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_show_data ON "show_data" (mal_id ASC )')
            cursor.connection.commit()

    @staticmethod
    def build_episode_table():
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS episodes (mal_id INTEGER NOT NULL, '
                           'season INTEGER NOT NULL, '
                           'kodi_meta BLOB NOT NULL, '
                           'last_updated TEXT NOT NULL, '
                           'number INTEGER NOT NULL, '
                           'filler TEXT, '
                           'anidb_ep_id INTEGER, '
                           'FOREIGN KEY(mal_id) REFERENCES shows(mal_id) ON DELETE CASCADE)')
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_episodes ON episodes (mal_id ASC, season ASC, number ASC)')
            cursor.connection.commit()

    @staticmethod
    def build_sync_activities():
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS activities (sync_id INTEGER PRIMARY KEY, otaku_version TEXT NOT NULL)')
            cursor.connection.commit()

    @staticmethod
    def migrate_to_precomputed_metadata():
        """
        PERFORMANCE MIGRATION: Add new columns for Seren-style pre-computed metadata.
        This enables smooth navigation in Arctic Fuse 2 by storing ready-to-use JSON data
        instead of computing metadata during list rendering.

        New columns in 'shows' table:
        - info TEXT: Complete info dict for InfoTagVideo (pre-computed, stored as JSON)
        - cast TEXT: Complete cast array (pre-computed, stored as JSON)
        - art TEXT: Complete art dict (pre-computed, stored as JSON)
        - last_updated TEXT: Timestamp for cache invalidation

        Migration is safe - adds columns if they don't exist, preserves existing data.
        """
        with SQL(control.malSyncDB) as cursor:
            # Check if new columns already exist
            cursor.execute("PRAGMA table_info(shows)")
            columns = {row['name'] for row in cursor.fetchall()}

            # Add new pre-computed metadata columns if they don't exist
            if 'info' not in columns:
                control.log("Adding 'info' column to shows table for pre-computed metadata")
                cursor.execute('ALTER TABLE shows ADD COLUMN info TEXT')

            if 'cast' not in columns:
                control.log("Adding 'cast' column to shows table for pre-computed metadata")
                cursor.execute('ALTER TABLE shows ADD COLUMN cast TEXT')

            if 'art' not in columns:
                control.log("Adding 'art' column to shows table for pre-computed metadata")
                cursor.execute('ALTER TABLE shows ADD COLUMN art TEXT')

            if 'last_updated' not in columns:
                control.log("Adding 'last_updated' column to shows table")
                cursor.execute('ALTER TABLE shows ADD COLUMN last_updated TEXT')

            # Also add last_updated to shows_meta for tracking fanart/tmdb/tvdb updates
            cursor.execute("PRAGMA table_info(shows_meta)")
            meta_columns = {row['name'] for row in cursor.fetchall()}

            if 'last_updated' not in meta_columns:
                control.log("Adding 'last_updated' column to shows_meta table")
                cursor.execute('ALTER TABLE shows_meta ADD COLUMN last_updated TEXT')

            cursor.connection.commit()
            control.log("Pre-computed metadata migration complete")

    def re_build_database(self, silent=False):
        import service
        import os

        if not silent:
            confirm = control.yesno_dialog(control.ADDON_NAME, control.lang(30032))
            if confirm == 0:
                return

        service.update_mappings_db()
        service.update_dub_json()

        # Properly delete the SQLite database file instead of corrupting it with 'w' mode
        try:
            if os.path.exists(control.malSyncDB):
                os.remove(control.malSyncDB)
                control.log('Deleted existing malSync.db for rebuild', level='info')
        except Exception as e:
            control.log(f'Error deleting malSync.db: {e}', level='error')

        self.build_sync_activities()
        self.build_show_table()
        self.build_showmeta_table()
        self.build_episode_table()
        self.build_show_data_table()

        self.set_base_activites()
        self.refresh_activites()
        if not silent:
            control.notify(f'{control.ADDON_NAME}: Database', 'Metadata Database Successfully Cleared', sound=False)

    def migration_process(self):
        import json
        import xbmc

        # Retrieve current settings
        watchlist_update_enabled = control.getBool('watchlist.update.enabled')
        watchlist_update_flavor = control.getSetting('watchlist.update.flavor')
        watchlist_update_percent = control.getInt('watchlist.update.percent')
        watchlist_sync_enabled = control.getBool('watchlist.sync.enabled')
        anilist_enabled = control.getBool('anilist.enabled')
        anilist_username = control.getSetting('anilist.username')
        anilist_token = control.getSetting('anilist.token')
        anilist_userid = control.getSetting('anilist.userid')
        mal_enabled = control.getBool('mal.enabled')
        mal_username = control.getSetting('mal.username')
        mal_authvar = control.getSetting('mal.authvar')
        mal_refresh = control.getSetting('mal.refresh')
        mal_token = control.getSetting('mal.token')
        mal_expiry = control.getInt('mal.expiry')
        kitsu_enabled = control.getBool('kitsu.enabled')
        kitsu_username = control.getSetting('kitsu.username')
        kitsu_authvar = control.getSetting('kitsu.authvar')
        kitsu_password = control.getSetting('kitsu.password')
        kitsu_refresh = control.getSetting('kitsu.refresh')
        kitsu_token = control.getSetting('kitsu.token')
        kitsu_userid = control.getSetting('kitsu.userid')
        kitsu_expiry = control.getInt('kitsu.expiry')
        simkl_enabled = control.getBool('simkl.enabled')
        simkl_username = control.getSetting('simkl.username')
        simkl_token = control.getSetting('simkl.token')
        first_time = False
        version = control.ADDON_VERSION

        # First, clear existing settings
        control.clear_settings(True)

        # Save all these settings to migrationSettings (migration.json)
        migration_data = {
            "watchlist.update.enabled": watchlist_update_enabled,
            "watchlist.update.flavor": watchlist_update_flavor,
            "watchlist.update.percent": watchlist_update_percent,
            "watchlist.sync.enabled": watchlist_sync_enabled,
            "anilist.enabled": anilist_enabled,
            "anilist.username": anilist_username,
            "anilist.token": anilist_token,
            "anilist.userid": anilist_userid,
            "mal.enabled": mal_enabled,
            "mal.username": mal_username,
            "mal.authvar": mal_authvar,
            "mal.refresh": mal_refresh,
            "mal.token": mal_token,
            "mal.expiry": mal_expiry,
            "kitsu.enabled": kitsu_enabled,
            "kitsu.username": kitsu_username,
            "kitsu.authvar": kitsu_authvar,
            "kitsu.password": kitsu_password,
            "kitsu.refresh": kitsu_refresh,
            "kitsu.token": kitsu_token,
            "kitsu.userid": kitsu_userid,
            "kitsu.expiry": kitsu_expiry,
            "simkl.enabled": simkl_enabled,
            "simkl.username": simkl_username,
            "simkl.token": simkl_token,
            "first_time": first_time,
            "version": version,
        }
        try:
            with open(control.migrationSettings, 'w', encoding='utf-8') as f:
                json.dump(migration_data, f, indent=4, sort_keys=True)
        except Exception as e:
            control.log(f"Error writing migration settings: {e}", level='error')

        # Remove old addons
        try:
            import shutil
            import os

            addon_ids = ['script.otaku.mappings', 'script.otaku.themepak']
            for addon_id in addon_ids:
                addon_path = os.path.join(control.ADDONS_PATH, addon_id)
                if os.path.exists(addon_path):
                    shutil.rmtree(addon_path)
        except Exception as e:
            control.log(f"Error removing old addons: {e}", level='error')

        # Inform user and force restart Kodi
        control.ok_dialog(control.ADDON_NAME, "Otaku has gotten a major update and requires a force restart to complete the watchlist migration.\nPlease restart Otaku to complete the migration.")
        xbmc.executebuiltin('Quit')
