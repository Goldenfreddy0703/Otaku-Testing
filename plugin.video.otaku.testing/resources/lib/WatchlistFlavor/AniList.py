import random
import pickle

from resources.lib.ui import utils, client, control, get_meta, database
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase
from resources.lib.ui.divide_flavors import div_flavor
from resources.lib.endpoints import simkl, anilist


class AniListWLF(WatchlistFlavorBase):
    _NAME = "anilist"
    _URL = "https://graphql.anilist.co"
    _TITLE = "AniList"
    _IMAGE = "anilist.png"

    def __headers(self):
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        return headers

    def login(self):
        query = '''
        query ($name: String) {
            User(name: $name) {
                id
            }
        }
        '''

        variables = {
            "name": self.username
        }

        r = client.post(self._URL, headers=self.__headers(), json_data={'query': query, 'variables': variables})
        results = r.json() if r else None
        if results is None:
            control.setSetting('anilist.token', '')
            control.setSetting('anilist.username', '')
            return
        userId = results['data']['User']['id']
        login_data = {
            'userid': str(userId)
        }
        return login_data

    def __get_sort(self):
        sort_types = [None, None, 'PROGRESS', 'UPDATED_TIME_DESC', 'ADDED_TIME_DESC']
        return sort_types[int(self.sort)]

    def watchlist(self):
        statuses = [
            ("Next Up", "CURRENT?next_up=true", 'next_up.png'),
            ("Current", "CURRENT", 'currently_watching.png'),
            ("Rewatching", "REPEATING", 'rewatching.png'),
            ("Plan to Watch", "PLANNING", 'want_to_watch.png'),
            ("Paused", "PAUSED", 'on_hold.png'),
            ("Completed", "COMPLETED", 'completed.png'),
            ("Dropped", "DROPPED", 'dropped.png')
        ]
        return [utils.allocate_item(res[0], f'watchlist_status_type/{self._NAME}/{res[1]}', True, False, [], res[2], {}) for res in statuses]

    def _base_watchlist_view(self, res):
        url = f'watchlist_status_type/{self._NAME}/{res[1]}'
        return [utils.allocate_item(res[0], url, True, False, [], f'{res[0].lower()}.png', {})]

    @staticmethod
    def action_statuses():
        actions = [
            ("Add to Current", "CURRENT"),
            ("Add to Rewatching", "REPEATING"),
            ("Add to Planning", "PLANNING"),
            ("Add to Paused", "PAUSED"),
            ("Add to Completed", "COMPLETED"),
            ("Add to Dropped", "DROPPED"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]
        return actions

    def get_watchlist_status(self, status, next_up, offset, page):
        query = '''
        query ($userId: Int, $userName: String, $status: MediaListStatus, $type: MediaType, $sort: [MediaListSort], $forceSingleCompletedList: Boolean) {
            MediaListCollection(userId: $userId, userName: $userName, status: $status, type: $type, sort: $sort, forceSingleCompletedList: $forceSingleCompletedList) {
                lists {
                    entries {
                        ...mediaListEntry
                        }
                    }
                }
            }

        fragment mediaListEntry on MediaList {
            id
            mediaId
            status
            progress
            media {
                id
                idMal
                title {
                    userPreferred,
                    romaji,
                    english
                }
                coverImage {
                    extraLarge
                }
                bannerImage
                startDate {
                    year,
                    month,
                    day
                }
                nextAiringEpisode {
                    episode,
                    airingAt
                }
                description
                synonyms
                format
                status
                episodes
                genres
                duration
                countryOfOrigin
                averageScore
                characters (
                    page: 1,
                    sort: ROLE,
                    perPage: 10,
                ) {
                    edges {
                        node {
                            name {
                                userPreferred
                            }
                        }
                        voiceActors (language: JAPANESE) {
                            name {
                                userPreferred
                            }
                            image {
                                large
                            }
                        }
                    }
                }
                studios {
                    edges {
                        node {
                            name
                        }
                    }
                }
                trailer {
                    id
                    site
                }
            }
        }
        '''

        variables = {
            'userId': int(self.user_id),
            'username': self.username,
            'status': status,
            'type': 'ANIME',
            'sort': self.__get_sort(),
            'forceSingleCompletedList': False
        }
        return self.process_status_view(query, variables, next_up)

    def process_status_view(self, query, variables, next_up):
        r = client.post(self._URL, headers=self.__headers(), json_data={'query': query, 'variables': variables})
        results = r.json() if r else {}
        lists = results['data']['MediaListCollection']['lists']
        entries = []
        for mlist in lists:
            for entrie in mlist['entries']:
                if entrie not in entries:
                    entries.append(entrie)
        get_meta.collect_meta(entries)

        # PERFORMANCE: Get MAL IDs (prefer API, fallback to mappings database)
        mal_ids = []
        for entry in entries:
            # Try API response first
            mal_id = entry['media'].get('idMal')

            # Fallback to mappings database if API doesn't have it
            if not mal_id:
                anilist_id = entry['media'].get('id')
                if anilist_id:
                    mappings = database.get_mappings(anilist_id, 'anilist_id')
                    mal_id = mappings.get('mal_id')

            if mal_id:
                mal_ids.append(int(mal_id))

        show_list = database.get_show_list(mal_ids) if mal_ids else {}

        # If sorting by title, sort manually alphabetically.
        if int(self.sort) == 0:
            entries.sort(key=lambda entry: (entry['media']['title'].get(self.title_lang) or "").lower())

        # If sorting by score, sort manually by score.
        if int(self.sort) == 1:
            entries.sort(key=lambda entry: entry['media']['averageScore'], reverse=True)

        # If oder is descending, reverse the order.
        if int(self.order) == 1:
            entries.reverse()

        # If next_up is True, reverse the order if needed.
        if next_up:
            all_results = [self._base_next_up_view(entry, show_list) for entry in entries]
        else:
            all_results = [self.base_watchlist_status_view(entry, show_list) for entry in entries]
        return all_results

    @div_flavor
    def base_watchlist_status_view(self, res, show_list=None, mal_dub=None):
        progress = res['progress']
        res = res['media']
        anilist_id = res['id']

        # Get MAL ID (prefer API, fallback to mappings database)
        mal_id = res.get('idMal')
        if not mal_id:
            mappings = database.get_mappings(anilist_id, 'anilist_id')
            mal_id = mappings.get('mal_id')

        if mal_id:
            mal_id = int(mal_id)

        if not mal_id:
            control.log(f"Mal ID not found for {anilist_id}", level='warning')

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        # PERFORMANCE: Get pre-computed metadata from batch query (Seren-style, no pickle!)
        precomputed_info = None
        precomputed_cast = None
        art_dict = {}

        if show_list and mal_id in show_list:
            show_data = show_list[mal_id]
            art_dict = show_data['art'] or {}
            precomputed_info = show_data['info']
            precomputed_cast = show_data['cast']

        title = res['title'].get(self.title_lang) or res['title'].get('userPreferred')

        # Build info dict from AniList API response
        info = {
            'UniqueIDs': {
                'anilist_id': str(anilist_id),
                'mal_id': str(mal_id),
                **database.get_unique_ids(anilist_id, 'anilist_id'),
                **database.get_unique_ids(mal_id, 'mal_id')
            },
            'title': title,
            'genre': res.get('genres'),
            'status': res.get('status'),
            'mediatype': 'tvshow',
            'country': [res.get('countryOfOrigin', '')],
            'studio': [x['node'].get('name') for x in res['studios'].get('edges')]
        }

        if res['episodes'] != 0 and progress == res['episodes']:
            info['playcount'] = 1

        try:
            info['duration'] = res.get('duration') * 60
        except TypeError:
            pass

        try:
            if res['trailer']['site'] == 'youtube':
                info['trailer'] = f"plugin://plugin.video.youtube/play/?video_id={res['trailer']['id']}"
            else:
                info['trailer'] = f"plugin://plugin.video.dailymotion_com/?url={res['trailer']['id']}&mode=playVideo"
        except TypeError:
            pass

        try:
            info['rating'] = {'score': res.get('averageScore') / 10.0}
        except TypeError:
            pass

        # Plot - PERFORMANCE: Use pre-computed as fallback
        desc = res.get('description')
        if desc:
            desc = desc.replace('<i>', '[I]').replace('</i>', '[/I]')
            desc = desc.replace('<b>', '[B]').replace('</b>', '[/B]')
            desc = desc.replace('<br>', '[CR]')
            desc = desc.replace('\n', '')
            info['plot'] = desc
        elif precomputed_info and precomputed_info.get('plot'):
            info['plot'] = precomputed_info['plot']

        try:
            start_date = res.get('startDate')
            info['aired'] = '{}-{:02}-{:02}'.format(start_date['year'], start_date['month'], start_date['day'])
        except TypeError:
            pass

        # Cast - PERFORMANCE: Use pre-computed as fallback
        cast = []
        try:
            for i, x in enumerate(res['characters']['edges']):
                role = x['node']['name']['userPreferred']
                actor = x['voiceActors'][0]['name']['userPreferred']
                actor_hs = x['voiceActors'][0]['image'].get('large')
                cast.append({'name': actor, 'role': role, 'thumbnail': actor_hs, 'index': i})
                info['cast'] = cast
        except IndexError:
            if precomputed_cast:
                info['cast'] = precomputed_cast

        # PERFORMANCE: Use pre-computed artwork from art_dict (no pickle!)
        anilist_image = res['coverImage']['extraLarge']
        image = art_dict.get('icon') or art_dict.get('poster') or anilist_image
        poster = art_dict.get('poster') or anilist_image
        fanart = art_dict.get('fanart') or anilist_image
        banner = art_dict.get('banner') or res.get('bannerImage')

        base = {
            "name": '%s - %d/%d' % (title, progress, res['episodes'] if res['episodes'] else 0),
            "url": f'watchlist_to_ep/{mal_id}/{progress}',
            "image": image,
            "poster": poster,
            'fanart': fanart,
            "banner": banner,
            "info": info
        }

        # Add extra Fanart.tv artwork from pre-computed art_dict
        if art_dict.get('landscape') or art_dict.get('thumb'):
            base['landscape'] = art_dict.get('landscape') or art_dict.get('thumb')
        if art_dict.get('clearart'):
            base['clearart'] = art_dict.get('clearart')
        if art_dict.get('clearlogo'):
            base['clearlogo'] = art_dict.get('clearlogo')

        if res['format'] == 'MOVIE' and res['episodes'] == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)

    @div_flavor
    def _base_next_up_view(self, res, show_list=None, mal_dub=None):
        progress = res['progress']
        res = res['media']

        anilist_id = res['id']

        # Get MAL ID (prefer API, fallback to mappings database)
        mal_id = res.get('idMal')
        if not mal_id:
            mappings = database.get_mappings(anilist_id, 'anilist_id')
            mal_id = mappings.get('mal_id')

        if mal_id:
            mal_id = int(mal_id)

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        # PERFORMANCE: Get pre-computed metadata from batch query (Seren-style, no pickle!)
        precomputed_info = None
        precomputed_cast = None
        art_dict = {}

        if show_list and mal_id in show_list:
            show_data = show_list[mal_id]
            art_dict = show_data['art'] or {}
            precomputed_info = show_data['info']
            precomputed_cast = show_data['cast']

        next_up = progress + 1
        episode_count = res['episodes'] if res['episodes'] else 0

        if not control.getBool('playlist.unaired'):
            airing_episode = simkl.Simkl().get_calendar_data(mal_id)
            if not airing_episode:
                airing_episode = anilist.Anilist().get_airing_calendar(mal_id)

            if airing_episode:
                episode_count = airing_episode

        base_title = res['title'].get(self.title_lang) or res['title'].get('userPreferred')
        title = f"{base_title} - {next_up}/{episode_count}"
        poster = image = res['coverImage']['extraLarge']

        if (0 < episode_count < next_up) or (res['nextAiringEpisode'] and next_up == res['nextAiringEpisode']['episode']):
            return None

        if mal_id:
            mal_id, next_up_meta, show = self._get_next_up_meta(mal_id, progress)
        else:
            next_up_meta = None
        if next_up_meta:
            if next_up_meta.get('title'):
                title = f"{title} - {next_up_meta['title']}"
            if next_up_meta.get('image'):
                image = next_up_meta['image']
            plot = next_up_meta.get('plot')
            aired = next_up_meta.get('aired')
        else:
            plot = aired = None

        info = {
            'UniqueIDs': {
                'anilist_id': str(anilist_id),
                'mal_id': str(mal_id),
                **database.get_unique_ids(anilist_id, 'anilist_id'),
                **database.get_unique_ids(mal_id, 'mal_id')
            },
            'episode': next_up,
            'title': title,
            'tvshowtitle': res['title']['userPreferred'],
            'plot': plot,
            'genre': res.get('genres'),
            'mediatype': 'episode',
            'aired': aired
        }

        # PERFORMANCE: Use pre-computed artwork from art_dict (no pickle!)
        fanart = art_dict.get('fanart') or image

        base = {
            "name": title,
            "url": f"watchlist_to_ep/{mal_id}/{progress}",
            "image": image,
            "info": info,
            "fanart": fanart,
            "poster": poster
        }

        # Add extra Fanart.tv artwork from pre-computed art_dict
        if art_dict.get('landscape') or art_dict.get('thumb'):
            base['landscape'] = art_dict.get('landscape') or art_dict.get('thumb')
        if art_dict.get('clearart'):
            base['clearart'] = art_dict.get('clearart')
        if art_dict.get('clearlogo'):
            base['clearlogo'] = art_dict.get('clearlogo')

        if res['format'] == 'MOVIE' and res['episodes'] == 1:
            base['url'] = f"play_movie/{mal_id}/"
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        if next_up_meta:
            base['url'] = f"play/{mal_id}/{next_up}"
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)

    def get_watchlist_anime_entry(self, mal_id):
        query = '''
        query ($mediaId: Int) {
            Media (idMal: $mediaId) {
                id
                mediaListEntry {
                    id
                    mediaId
                    status
                    score
                    progress
                    user {
                        id
                        name
                    }
                }
            }
        }
        '''

        variables = {
            'mediaId': mal_id
        }

        r = client.post(self._URL, headers=self.__headers(), json_data={'query': query, 'variables': variables})
        results = r.json()['data']['Media']['mediaListEntry'] if r else {}
        if not results:
            return {}
        anime_entry = {
            'eps_watched': results.get('progress'),
            'status': results['status'],
            'score': results['score']
        }
        return anime_entry

    def save_completed(self):
        import json
        data = self.get_user_anime_list('COMPLETED')
        completed = {}
        for dat in data:
            for entrie in dat['entries']:
                if entrie['media']['episodes']:
                    completed[str(entrie['media']['idMal'])] = int(entrie['media']['episodes'])
        with open(control.completed_json, 'w') as file:
            json.dump(completed, file)

    def get_user_anime_list(self, status):
        query = '''
        query ($userId: Int, $userName: String, $status: MediaListStatus, $type: MediaType, $sort: [MediaListSort]) {
            MediaListCollection(userId: $userId, userName: $userName, status: $status, type: $type, sort: $sort) {
                lists {
                    entries {
                        id
                        mediaId
                        progress
                        media {
                            id
                            idMal
                            episodes
                        }
                    }
                }
            }
        }
        '''

        variables = {
            'userId': int(self.user_id),
            'username': self.username,
            'status': status,
            'type': 'ANIME',
            'sort': self.__get_sort()
        }
        r = client.post(self._URL, headers=self.__headers(), json_data={'query': query, 'variables': variables})
        results = r.json() if r else {}
        return results['data']['MediaListCollection']['lists'] if 'data' in results else []

    def get_watchlist_anime_info(self, anilist_id):
        query = '''
        query ($mediaId: Int) {
            Media (id: $mediaId) {
                id
                mediaListEntry {
                    id
                    mediaId
                    status
                    score
                    progress
                }
            }
        }
        '''

        variables = {
            'mediaId': anilist_id
        }

        r = client.post(self._URL, headers=self.__headers(), json_data={'query': query, 'variables': variables})
        results = r.json() if r else {}
        return results

    def update_list_status(self, mal_id, status):
        anilist_id = self._get_mapping_id(mal_id, 'anilist_id')
        if not anilist_id:
            return False
        query = '''
        mutation ($mediaId: Int, $status: MediaListStatus) {
            SaveMediaListEntry (mediaId: $mediaId, status: $status) {
                id
                status
            }
        }
        '''

        variables = {
            'mediaId': int(anilist_id),
            'status': status
        }

        r = client.post(self._URL, headers=self.__headers(), json_data={'query': query, 'variables': variables})
        return r and r.ok

    def update_num_episodes(self, mal_id, episode):
        anilist_id = self._get_mapping_id(mal_id, 'anilist_id')
        if not anilist_id:
            return False
        query = '''
        mutation ($mediaId: Int, $progress : Int, $status: MediaListStatus) {
            SaveMediaListEntry (mediaId: $mediaId, progress: $progress, status: $status) {
                id
                progress
                status
            }
        }
        '''

        variables = {
            'mediaId': int(anilist_id),
            'progress': int(episode)
        }

        r = client.post(self._URL, headers=self.__headers(), json_data={'query': query, 'variables': variables})
        return r and r.ok

    def update_score(self, mal_id, score):
        anilist_id = self._get_mapping_id(mal_id, 'anilist_id')
        if not anilist_id:
            return False
        query = '''
        mutation ($mediaId: Int, $score: Float) {
            SaveMediaListEntry (mediaId: $mediaId, score: $score) {
                id
                score
            }
        }
        '''

        variables = {
            'mediaId': int(anilist_id),
            'score': float(score)
        }

        r = client.post(self._URL, headers=self.__headers(), json_data={'query': query, 'variables': variables})
        return r and r.ok

    def delete_anime(self, mal_id):
        anilist_id = self._get_mapping_id(mal_id, 'anilist_id')
        if not anilist_id:
            return False
        media_entry = self.get_watchlist_anime_info(anilist_id)['data']['Media']['mediaListEntry']
        if media_entry:
            list_id = media_entry['id']
        else:
            return True
        query = '''
        mutation ($id: Int) {
            DeleteMediaListEntry (id: $id) {
                deleted
            }
        }
        '''

        variables = {
            'id': int(list_id)
        }
        r = client.post(self._URL, headers=self.__headers(), json_data={'query': query, 'variables': variables})
        return r and r.ok
