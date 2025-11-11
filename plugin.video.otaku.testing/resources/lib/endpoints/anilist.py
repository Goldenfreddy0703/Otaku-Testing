from resources.lib.ui import client, control


class Anilist:
    _BASE_URL = "https://graphql.anilist.co"

    def get_anilist_ratings_batch(self, mal_ids):
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
