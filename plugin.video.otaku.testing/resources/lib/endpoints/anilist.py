import json
import datetime
import time
import os
from resources.lib.ui import client, database, control


class Anilist:
    _BASE_URL = "https://graphql.anilist.co"

    def update_calendar(self):
        today = datetime.date.today()
        today_ts = int(time.mktime(today.timetuple()))
        weekStart = today_ts - 86400
        weekEnd = today_ts + (86400 * 6)
        variables = {
            'weekStart': weekStart,
            'weekEnd': weekEnd,
            'page': 1
        }

        anilist_cache = []

        for i in range(0, 4):
            popular = self.get_airing_calendar_res(variables)
            anilist_cache.append(popular)

            if not popular['pageInfo']['hasNextPage']:
                break

            variables['page'] += 1

        self.set_cached_data(anilist_cache)

    def get_airing_calendar(self, mal_id, page=1):
        meta_ids = database.get_mappings(mal_id, 'mal_id')
        anilist_id = meta_ids.get('anilist_id')
        anilist_cache = self.get_cached_data()
        if anilist_cache:
            airing_episode = self.extract_episode_number(anilist_cache, anilist_id)
            return airing_episode
        else:
            today = datetime.date.today()
            today_ts = int(time.mktime(today.timetuple()))
            weekStart = today_ts - 86400
            weekEnd = today_ts + (86400 * 6)
            variables = {
                'weekStart': weekStart,
                'weekEnd': weekEnd,
                'page': page
            }

            anilist_cache = []

            for i in range(0, 4):
                popular = self.get_airing_calendar_res(variables, page)
                anilist_cache.append(popular)

                if not popular['pageInfo']['hasNextPage']:
                    break

                page += 1
                variables['page'] = page

            self.set_cached_data(anilist_cache)
            airing_episode = self.extract_episode_number(anilist_cache, anilist_id)
            return airing_episode

    def get_airing_calendar_res(self, variables, page=1):
        query = '''
        query (
                $weekStart: Int,
                $weekEnd: Int,
                $page: Int,
        ){
            Page(page: $page) {
                pageInfo {
                        hasNextPage
                        total
                }

                airingSchedules(
                        airingAt_greater: $weekStart
                        airingAt_lesser: $weekEnd
                ) {
                    id
                    episode
                    airingAt
                    media {
                        id
                        idMal
                        title {
                                romaji
                                userPreferred
                                english
                        }
                        description
                        countryOfOrigin
                        genres
                        averageScore
                        isAdult
                        rankings {
                                rank
                                type
                                season
                        }
                        coverImage {
                                extraLarge
                        }
                        bannerImage
                    }
                }
            }
        }
        '''

        r = client.request(self._BASE_URL, post={'query': query, 'variables': variables}, jpost=True)
        results = json.loads(r)

        if "errors" in results.keys():
            return

        json_res = results.get('data', {}).get('Page')

        if json_res:
            return json_res

    def extract_episode_number(self, anilist_cache, anilist_id):
        if not anilist_cache:
            return None

        for item in anilist_cache:
            for schedule in item['airingSchedules']:
                if schedule['media']['id'] == anilist_id:
                    airing_at_timestamp = schedule['airingAt']
                    airing_at_datetime = datetime.datetime.fromtimestamp(airing_at_timestamp, datetime.timezone.utc)

                    # Check if the episode has already aired
                    if airing_at_datetime <= datetime.datetime.now(datetime.timezone.utc):
                        return schedule['episode']
                    else:
                        return schedule['episode'] - 1

        return None

    def get_cached_data(self):
        if os.path.exists(control.anilist_calendar_json):
            with open(control.anilist_calendar_json, 'r') as f:
                return json.load(f)
        return None

    def set_cached_data(self, data):
        with open(control.anilist_calendar_json, 'w') as f:
            json.dump(data, f)
