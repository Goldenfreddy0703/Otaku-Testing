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

        r = client.post(self._BASE_URL, json_data={'query': query, 'variables': variables})
        results = r.json()

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

    @staticmethod
    def get_anilist_by_mal_ids(mal_ids, page=1, media_type="ANIME"):
        _ANILIST_BASE_URL = "https://graphql.anilist.co"

        query = '''
        query ($page: Int, $malIds: [Int], $type: MediaType) {
          Page(page: $page) {
            pageInfo {
              hasNextPage
              total
            }
            media(idMal_in: $malIds, type: $type) {
              id
              idMal
              title {
                romaji
                english
              }
              coverImage {
                extraLarge
              }
              bannerImage
              startDate {
                year
                month
                day
              }
              description
              synonyms
              format
              episodes
              status
              genres
              duration
              countryOfOrigin
              averageScore
              characters(
                page: 1
                sort: ROLE
                perPage: 10
              ) {
                edges {
                  node {
                    name {
                      userPreferred
                    }
                  }
                  voiceActors(language: JAPANESE) {
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
              stats {
                scoreDistribution {
                  score
                  amount
                }
              }
            }
          }
        }
        '''

        all_media = []
        page = 1
        while True:
            variables = {
                "page": page,
                "malIds": mal_ids,
                "type": media_type
            }
            result = client.post(_ANILIST_BASE_URL, json_data={'query': query, 'variables': variables})
            results = result.json()
            page_data = results.get('data', {}).get('Page', {})
            media = page_data.get('media', [])
            all_media.extend(media)
            has_next = page_data.get('pageInfo', {}).get('hasNextPage', False)
            if not has_next:
                break
            page += 1
        return all_media

    @staticmethod
    def get_anilist_ratings_batch(mal_ids):
        """
        Get AniList ratings for multiple anime using MAL IDs in batch
        Fetches averageScore and meanScore from AniList API
        
        Args:
            mal_ids (list): List of MyAnimeList IDs (integers or strings)
            
        Returns:
            dict: Dictionary mapping MAL IDs to their AniList ratings
                  Format: {mal_id: {'anilist_score': score}}
                  Score is on 0-100 scale (e.g., 75 for 7.5/10)
        """
        if not mal_ids:
            return {}
        
        _ANILIST_BASE_URL = "https://graphql.anilist.co"
        
        # Filter valid MAL IDs and convert to integers
        valid_mal_ids = []
        for mal_id in mal_ids:
            if mal_id and mal_id != 0:
                try:
                    valid_mal_ids.append(int(mal_id))
                except (ValueError, TypeError):
                    continue
        
        if not valid_mal_ids:
            return {}
        
        # AniList GraphQL query for ratings only
        query = '''
        query ($page: Int, $malIds: [Int], $type: MediaType) {
          Page(page: $page, perPage: 50) {
            pageInfo {
              hasNextPage
              total
            }
            media(idMal_in: $malIds, type: $type) {
              id
              idMal
              averageScore
              meanScore
            }
          }
        }
        '''
        
        ratings_map = {}
        page = 1
        
        try:
            while True:
                variables = {
                    "page": page,
                    "malIds": valid_mal_ids,
                    "type": "ANIME"
                }
                
                result = client.post(_ANILIST_BASE_URL, json_data={'query': query, 'variables': variables})
                
                if not result:
                    break
                
                results = result.json()
                
                # Check for errors
                if "errors" in results:
                    control.log(f"AniList API error: {results['errors']}", "error")
                    break
                
                page_data = results.get('data', {}).get('Page', {})
                media_list = page_data.get('media', [])
                
                # Process each anime's rating
                for media in media_list:
                    mal_id = media.get('idMal')
                    if not mal_id:
                        continue
                    
                    # AniList averageScore is already on 0-100 scale
                    avg_score = media.get('averageScore', 0)
                    mean_score = media.get('meanScore', 0)
                    
                    # Use averageScore (community rating), fallback to meanScore if not available
                    score = avg_score if avg_score else mean_score
                    
                    ratings_map[int(mal_id)] = {
                        'anilist_score': int(score) if score else 0
                    }
                
                # Check if there are more pages
                has_next = page_data.get('pageInfo', {}).get('hasNextPage', False)
                if not has_next:
                    break
                
                page += 1
            
            return ratings_map
        
        except Exception as e:
            control.log(f"Error fetching AniList ratings batch: {str(e)}", "error")
            return {}


# Convenience functions
def get_anilist_ratings_for_mal_ids(mal_ids):
    """
    Get AniList ratings for multiple MAL IDs
    
    Args:
        mal_ids (list): List of MyAnimeList IDs
        
    Returns:
        dict: Dictionary mapping MAL IDs to AniList ratings
    """
    anilist = Anilist()
    return anilist.get_anilist_ratings_batch(mal_ids)
