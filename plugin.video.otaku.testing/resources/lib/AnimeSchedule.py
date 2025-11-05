import datetime

from resources.lib.ui import client, database, control, utils

BASE_URL = "https://animeschedule.net/api/v3"
WEBSITE_URL = "https://animeschedule.net"


class AnimeScheduleCalendar:
    """
    Fetches anime calendar data from AnimeSchedule.net API
    Filters and enriches data with MAL IDs and airing information
    Uses Bearer token authentication for timetables endpoints
    """

    def __init__(self):
        """Initialize with API credentials from database"""
        self.api_info = database.get_info('AnimeSchedule')
        if not self.api_info:
            control.log("AnimeSchedule API info not found in database", "error")
            self.token = None
        else:
            # Use 'client_secret' as the Bearer token
            self.token = self.api_info.get('client_secret')

        # Cache for /anime endpoint data (keyed by route)
        self._anime_cache = {}

    def get_calendar_data(self, days=7, types=['sub', 'dub', 'raw']):
        """
        Fetch calendar data using optimized two-step strategy:
        1. Fetch timetables (SUB, DUB, RAW)
        2. Fetch season anime until all pages exhausted

        Args:
            days (int): Number of days to fetch (default: 7 for weekly view)
            types (list): Release types to fetch ['sub', 'dub', 'raw']

        Returns:
            list: List of anime airing data with enriched information
        """
        try:
            if not self.token:
                control.log("AnimESchedule token not found, cannot fetch timetables", "warning")
                return []

            # Get current year and week
            today = datetime.datetime.now()
            year = today.year
            week = today.isocalendar()[1]
            
            # Determine current season
            month = today.month
            if month in [12, 1, 2]:
                season = 'winter'
            elif month in [3, 4, 5]:
                season = 'spring'
            elif month in [6, 7, 8]:
                season = 'summer'
            else:  # 9, 10, 11
                season = 'fall'

            # STEP 1: Fetch timetables and collect unique routes
            all_timetable_anime = []
            unique_routes = set()

            # Build parallel requests for all three timetables
            timetable_requests = []
            for release_type in types:
                timetable_requests.append({
                    'func': self._fetch_timetable,
                    'args': (release_type, year, week),
                    'kwargs': {}
                })

            # Execute all timetable fetches in parallel
            timetable_results = utils.parallel_fetch(timetable_requests, max_workers=3)

            # Process results
            for release_type, anime_data in zip(types, timetable_results):
                if anime_data:
                    for anime in anime_data:
                        route = anime.get('route')
                        all_timetable_anime.append({
                            'route': route,
                            'type': release_type,
                            'data': anime
                        })
                        unique_routes.add(route)

            unique_count = len(unique_routes)
            control.log(f"AnimESchedule: Found {unique_count} unique anime from timetables", "info")

            # STEP 2: Fetch season anime in parallel (fixed number of pages)
            season_anime = {}
            matched_routes = set()
            
            # Fetch first 10 pages (covers ~180 anime, enough for most ongoing seasons)
            max_pages_to_fetch = 10
            
            control.log(f"AnimESchedule: Fetching {max_pages_to_fetch} pages in parallel", "info")
            
            # Create parallel requests for multiple pages
            page_requests = [
                {
                    'func': self._fetch_season_anime,
                    'args': (year, season, page),
                    'kwargs': {}
                }
                for page in range(1, max_pages_to_fetch + 1)
            ]
            
            # Fetch all pages in parallel with 10 workers
            page_results = utils.parallel_fetch(page_requests, max_workers=10)
            
            # Process all results
            for page_data in page_results:
                if page_data:
                    for anime in page_data:
                        route = anime.get('route')
                        if route not in season_anime:
                            season_anime[route] = anime
                        
                        if route in unique_routes:
                            matched_routes.add(route)

            control.log(f"AnimESchedule: Matched {len(matched_routes)}/{unique_count} from season pages", "info")

            # STEP 3: Individual searches for unmatched routes (parallel with retry)
            unmatched_routes = unique_routes - matched_routes
            if unmatched_routes:
                control.log(f"AnimESchedule: Fetching {len(unmatched_routes)} unmatched routes individually", "info")
                
                # Create search requests for parallel fetching
                search_requests = [
                    {
                        'func': self._search_anime_by_route,
                        'args': (route,),
                        'kwargs': {}
                    }
                    for route in sorted(unmatched_routes)
                ]

                # Parallel search with 25 workers (increased from 20)
                search_results = utils.parallel_fetch(search_requests, max_workers=25)

                # Process results
                found_count = 0
                for result in search_results:
                    if result and isinstance(result, dict):
                        route = result.get('route')
                        if route and route in unmatched_routes:
                            season_anime[route] = result
                            matched_routes.add(route)
                            found_count += 1

                control.log(f"AnimESchedule: Individual fetch found {found_count}/{len(unmatched_routes)}", "info")

                # Retry any remaining failures with reduced workers (only if needed)
                still_unmatched = unmatched_routes - matched_routes
                if still_unmatched and len(still_unmatched) > 0:
                    import time
                    control.log(f"AnimESchedule: Retrying {len(still_unmatched)} failed routes", "info")
                    
                    # Only delay if many failures (>10) to avoid rate limiting
                    if len(still_unmatched) > 10:
                        time.sleep(0.5)
                    
                    retry_requests = [
                        {
                            'func': self._search_anime_by_route,
                            'args': (route,),
                            'kwargs': {}
                        }
                        for route in sorted(still_unmatched)
                    ]
                    
                    # Use 12 workers for retry (increased from 10)
                    retry_results = utils.parallel_fetch(retry_requests, max_workers=12)
                    
                    retry_found = 0
                    for result in retry_results:
                        if result and isinstance(result, dict):
                            route = result.get('route')
                            if route and route in still_unmatched:
                                season_anime[route] = result
                                matched_routes.add(route)
                                retry_found += 1
                    
                    control.log(f"AnimESchedule: Retry found {retry_found}/{len(still_unmatched)}", "info")

            control.log(f"AnimESchedule: Total enriched {len(matched_routes)}/{unique_count}", "info")

            # Process and return results
            all_anime = []

            for timetable_entry in all_timetable_anime:
                route = timetable_entry['route']
                release_type = timetable_entry['type']
                raw_anime = timetable_entry['data']

                # Get enriched data from season fetch
                enriched_data = season_anime.get(route)

                # Extract MAL ID
                mal_id = None
                if enriched_data:
                    mal_id = self._extract_mal_id(enriched_data)

                # Build anime entry
                anime_entry = {
                    'route': route,
                    'mal_id': mal_id,
                    'title': raw_anime.get('title'),
                    'romaji': raw_anime.get('romaji'),
                    'english': raw_anime.get('english'),
                    'native': raw_anime.get('native'),
                    'image': self._get_image_url(raw_anime),
                    'episode_number': raw_anime.get('episodeNumber'),
                    'total_episodes': enriched_data.get('episodes') if enriched_data else None,
                    'status': enriched_data.get('status') if enriched_data else None,
                    'air_type': release_type,
                    'airing_status': raw_anime.get('airingStatus'),
                    'episode_date': raw_anime.get('episodeDate'),
                    'length_min': raw_anime.get('lengthMin'),
                    'is_donghua': raw_anime.get('donghua', False),
                    'media_types': [m['name'] for m in raw_anime.get('mediaTypes', [])],
                    'genres': [g['name'] for g in enriched_data.get('genres', [])] if enriched_data else [],
                    'studios': [s['name'] for s in enriched_data.get('studios', [])] if enriched_data else [],
                    'description': enriched_data.get('description') if enriched_data else None,
                    'websites': enriched_data.get('websites', {}) if enriched_data else {},
                    'stats': enriched_data.get('stats', {}) if enriched_data else {},
                    'streams': raw_anime.get('streams', []),
                }

                all_anime.append(anime_entry)

            # Deduplicate by route
            unique_anime = {}
            for anime in all_anime:
                route = anime.get('route')
                if route not in unique_anime:
                    unique_anime[route] = anime

            result = list(unique_anime.values())

            mal_id_count = len([a for a in result if a.get('mal_id')])
            control.log(f"AnimESchedule: Returned {len(result)} anime with {mal_id_count} MAL IDs", "info")
            return result

        except Exception as e:
            control.log(f"Error fetching AnimeSchedule calendar: {str(e)}", "error")
            return []

    def _fetch_timetable(self, release_type, year, week):
        """
        Fetch timetable data from AnimESchedule API with Bearer token auth

        Args:
            release_type (str): 'sub', 'dub', or 'raw'
            year (int): Year (e.g., 2025)
            week (int): Week number (1-53)

        Returns:
            list: Anime data for the specified week
        """
        try:
            url = f"{BASE_URL}/timetables/{release_type}"
            params = {
                'year': year,
                'week': week
            }
            headers = {
                'Authorization': f'Bearer {self.token}'
            }

            # Note: client.get() might not support headers, so we use client directly
            response = client.get(url, params=params, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                control.log(f"Failed to fetch {release_type} timetable: {response.status_code}", "error")
                return None

        except Exception as e:
            control.log(f"Error in _fetch_timetable: {str(e)}", "error")
            return None

    def _fetch_season_anime(self, year, season, page):
        """
        Fetch anime for a specific season and year

        Args:
            year (int): Year (e.g., 2025)
            season (str): Season ('winter', 'spring', 'summer', 'fall')
            page (int): Page number (1-indexed)

        Returns:
            list: Anime list for the page, or empty list on error
        """
        try:
            url = f"{BASE_URL}/anime"
            params = {
                'year': year,
                'seasons': season,
                'airing-statuses': 'ongoing',
                'page': page
            }

            response = client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                anime_list = data.get('anime', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                return anime_list

            return []

        except Exception as e:
            control.log(f"Error fetching season anime page {page}: {str(e)}", "debug")
            return []

    def _search_anime_by_route(self, route):
        """
        Fetch anime by route slug using direct endpoint with retry logic

        Args:
            route (str): Anime route slug

        Returns:
            dict: Anime data if found, None otherwise
        """
        import time
        
        max_attempts = 2
        retry_delay = 0.2  # Reduced from 0.3 for faster retries
        
        for attempt in range(max_attempts):
            try:
                # Use direct route endpoint: /anime/{route}
                url = f"{BASE_URL}/anime/{route}"

                response = client.get(url, timeout=6)  # Reduced from 8 to 6 seconds

                if response.status_code == 200:
                    data = response.json()
                    # Direct endpoint returns single anime object, not a list
                    if data and isinstance(data, dict):
                        return data

                # If we got here, no results or bad status - try again
                if attempt < max_attempts - 1:
                    time.sleep(retry_delay)

            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep(retry_delay)
                else:
                    control.log(f"Error fetching route {route} after {max_attempts} attempts: {str(e)}", "debug")
        
        return None

    def _extract_mal_id(self, anime):
        """Extract MAL ID from anime data"""
        # Check websites.mal link for MAL ID
        websites = anime.get('websites', {})
        mal_link = websites.get('mal', '')

        if mal_link:
            # Extract from URL like "myanimelist.net/anime/5114/Title"
            parts = mal_link.split('/anime/')
            if len(parts) > 1:
                mal_id_str = parts[1].split('/')[0]
                try:
                    return int(mal_id_str)
                except ValueError:
                    pass

        return None

    def _get_image_url(self, anime):
        """Construct full image URL from route"""
        image_route = anime.get('imageVersionRoute')
        if image_route:
            return f"https://img.animeschedule.net/production/assets/public/img/{image_route}"
        return None

    def format_for_anichart(self, anime_list):
        """
        Transform enriched anime data into Anichart display format
        
        Args:
            anime_list (list): List of enriched anime entries from get_calendar_data()
            
        Returns:
            list: List of formatted anime items for Anichart window
        """
        from resources.lib.ui import control
        
        # Get user's title language preference (0=romaji, 1=english)
        title_lang_pref = control.getInt("titlelanguage")
        
        formatted_items = []
        
        for anime in anime_list:
            try:
                # Select title based on user preference
                if title_lang_pref == 1:  # English
                    title = anime.get('english') or anime.get('romaji') or anime.get('title')
                else:  # Romaji (default)
                    title = anime.get('romaji') or anime.get('english') or anime.get('title')
                
                # Format airing info for display
                airing_info = self._format_airing_info(anime)
                
                # Format stats
                stats = anime.get('stats', {})
                score = stats.get('averageScore', 0)
                popularity = stats.get('popularity', 0)
                rank = stats.get('rank', 0)
                
                # Format genres and studios
                genres = ', '.join(anime.get('genres', []))
                studios = ', '.join(anime.get('studios', []))
                
                # Format streams/episodes info
                streams = anime.get('streams', [])
                stream_info = self._format_streams(streams)
                
                # Build Anichart item
                anichart_item = {
                    'id': anime.get('mal_id') or anime.get('route'),
                    'release_title': title,
                    'title': title,
                    'romaji': anime.get('romaji', ''),
                    'english': anime.get('english', ''),
                    'native': anime.get('native', ''),
                    'poster': anime.get('image', ''),
                    'plot': anime.get('description', ''),
                    'genres': genres,
                    'studios': studios,
                    'episode_number': anime.get('episode_number', 0),
                    'total_episodes': anime.get('total_episodes', 0),
                    'status': anime.get('status', ''),
                    'airing_status': anime.get('airing_status', ''),
                    'episode_date': anime.get('episode_date', ''),
                    'length_min': anime.get('length_min', 0),
                    'media_type': ', '.join(anime.get('media_types', [])),
                    'air_type': anime.get('air_type', ''),
                    'is_donghua': 'Yes' if anime.get('is_donghua') else 'No',
                    'mal_id': anime.get('mal_id', 0),
                    'route': anime.get('route', ''),
                    # Stats
                    'averageScore': score,
                    'popularity': popularity,
                    'rank': rank,
                    # Airing info (detailed)
                    'ep_airingAt': airing_info,
                    'airing_info': str(airing_info),
                    # Streams
                    'streams': stream_info,
                    'websites': str(anime.get('websites', {})),
                }
                
                formatted_items.append(anichart_item)
                
            except Exception as e:
                control.log(f"Error formatting anime for Anichart: {str(e)}", "error")
                continue
        
        return formatted_items

    def _format_airing_info(self, anime):
        """Format airing information for display"""
        air_type = anime.get('air_type', '')
        episode_date = anime.get('episode_date', '')
        episode_num = anime.get('episode_number', 0)
        
        if episode_date and episode_date != '0001-01-01T00:00:00Z':
            try:
                # Parse ISO format date
                dt = datetime.datetime.fromisoformat(episode_date.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                date_str = episode_date
        else:
            date_str = 'TBA'
        
        # Format based on release type
        air_type_upper = air_type.upper() if air_type else 'UNKNOWN'
        
        return f"Ep. {episode_num} ({air_type_upper}): {date_str}"

    def _format_streams(self, streams):
        """Format streaming service information"""
        if not streams:
            return 'Not specified'
        
        stream_names = []
        for stream in streams:
            if isinstance(stream, dict):
                name = stream.get('name') or stream.get('title')
                if name:
                    stream_names.append(name)
            else:
                stream_names.append(str(stream))
        
        return ', '.join(stream_names) if stream_names else 'Not specified'

    def get_anime_by_mal_id(self, mal_id):
        """
        Get specific anime's data by MAL ID

        Args:
            mal_id (int): MyAnimeList ID

        Returns:
            dict: Anime data with airing information
        """
        try:
            params = {
                "mal-ids": mal_id
            }

            response = client.get(f"{BASE_URL}/anime", params=params)

            if response:
                data = response.json()
                anime_list = data.get('anime', [])

                if anime_list:
                    anime = anime_list[0]

                    enriched_anime = {
                        'mal_id': mal_id,
                        'route': anime.get('route'),
                        'title': anime.get('title'),
                        'image': self._get_image_url(anime),
                        'description': anime.get('description'),
                        'episodes': anime.get('episodes'),
                        'genres': [g['name'] for g in anime.get('genres', [])],
                        'status': anime.get('status'),
                        'studios': [s['name'] for s in anime.get('studios', [])],
                        'airing_info': {
                            'sub': {
                                'time': anime.get('subTime'),
                                'delayed_from': anime.get('subDelayedFrom'),
                                'delayed_until': anime.get('subDelayedUntil'),
                            },
                            'dub': {
                                'time': anime.get('dubTime'),
                                'delayed_from': anime.get('dubDelayedFrom'),
                                'delayed_until': anime.get('dubDelayedUntil'),
                            },
                            'delay_description': anime.get('delayedDesc'),
                        },
                        'stats': anime.get('stats', {}),
                        'websites': anime.get('websites', {}),
                        'raw_data': anime
                    }

                    return enriched_anime
                else:
                    control.log(f"No anime found for MAL ID: {mal_id}", "warning")
                    return None
            else:
                control.log(f"Failed to fetch anime data for MAL ID: {mal_id}", "error")
                return None

        except Exception as e:
            control.log(f"Error in get_anime_by_mal_id: {str(e)}", "error")
            return None


# Convenience functions for direct usage
def get_calendar(days=7):
    """Get calendar data for upcoming days"""
    scheduler = AnimeScheduleCalendar()
    return scheduler.get_calendar_data(days=days)


def get_anime_schedule(mal_id):
    """Get schedule for specific anime by MAL ID"""
    scheduler = AnimeScheduleCalendar()
    return scheduler.get_anime_by_mal_id(mal_id)
