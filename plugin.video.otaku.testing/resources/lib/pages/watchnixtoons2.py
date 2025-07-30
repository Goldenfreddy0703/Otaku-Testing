import base64
import codecs
import json
import pickle
import re
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup, SoupStrainer
from resources.lib.ui import control, database, client, source_utils
from resources.lib.ui.BrowserBase import BrowserBase


class Sources(BrowserBase):
    _BASE_URL = 'https://www.wcostream.tv'

    def get_sources(self, mal_id, episode):
        show = database.get_show(mal_id)
        database_meta = database.get_mappings(mal_id, 'mal_id')
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        season = database.get_episode(mal_id)['season']
        anime_media_episodes = database_meta.get('anime_media_episodes', {})
        global_media_episodes = database_meta.get('globel_media_episodes', {})
        title = kodi_meta.get('name')
        english_title = kodi_meta.get('ename')
        clean_title = self._clean_title(title)

        if season == 1:
            if database_meta and 'thetvdb_season' in database_meta:
                thetvdb_season = database_meta['thetvdb_season']
                if thetvdb_season == 'a' or thetvdb_season == 0:
                    season = None

        # Map episode number if anime_media_episodes and global_media_episodes are different
        mapped_episode = episode
        if anime_media_episodes and global_media_episodes:
            # Parse ranges like "1-13" and "13-25"
            anime_range = self._parse_episode_range(anime_media_episodes)
            global_range = self._parse_episode_range(global_media_episodes)

            if anime_range and global_range and anime_range != global_range:
                anime_start, anime_end = anime_range
                global_start, global_end = global_range

                # Convert episode to int for comparison
                episode_int = int(episode)

                # Check if episode is within anime range
                if anime_start <= episode_int <= anime_end:
                    # Map episode from anime range to global range
                    offset = episode_int - anime_start
                    mapped_episode = global_start + offset
                    control.log(f"Mapped episode {episode} to {mapped_episode}")

        # Use the new search and episode matching system
        sources = []

        # Try with title first, then english_title if no results
        search_title = title if title else english_title
        if not search_title:
            return []

        series_results = self.search_series(search_title)

        # If no results with main title, try english title
        if not series_results and english_title and english_title != title:
            series_results = self.search_series(english_title)

        if series_results:
            # Get episodes from the first (best match) series
            episodes = self.get_episodes_from_series(series_results[0]['url'])

            if episodes:
                # Find matching episode using season and mapped_episode
                episode_matches = self.find_episode_match(episodes, season, mapped_episode)

                if episode_matches:
                    control.log(f"\nFOUND EPISODE MATCHES:")
                    for i, match in enumerate(episode_matches):
                        control.log(f"{i+1}. ✓ {match['match_type']}: {match['title']}")
                        control.log(f"   URL: {match['url']}")
                        control.log(f"   Href: {match['href']}")

                    # Show the best match
                    best_match = episode_matches[0]
                    control.log(f"BEST EPISODE MATCH:")
                    control.log(f"Title: {best_match['title']}")
                    control.log(f"Match type: {best_match['match_type']}")
                    control.log(f"URL: {best_match['url']}")
                    control.log(f"Href: {best_match['href']}")
                else:
                    control.log(f"\nNo matching episode found for Season {season} Episode {episode}")
                    control.log("Here are the first 10 episodes:")
                    for i, ep in enumerate(episodes[:10]):
                        control.log(f"{i+1}. {ep['title']}")
                        control.log(f"   URL: {ep['url']}")










                    # best_match = episode_matches[0]
                    # # Create source from the best match
                    # source = {
                    #     'release_title': f'{search_title} - Season {season} Episode {mapped_episode}',
                    #     'hash': best_match['url'],
                    #     'type': 'embed',
                    #     'quality': 0,
                    #     'debrid_provider': '',
                    #     'provider': 'watchnixtoons2',
                    #     'size': 'NA',
                    #     'seeders': 0,
                    #     'byte_size': 0,
                    #     'info': [best_match['match_type']],
                    #     'lang': 3 if "dub" in best_match['title'].lower() else 2,
                    #     'channel': 3,
                    #     'sub': 1
                    # }
                    # sources.append(source)

        return sources

    def truncate_search_query(self, title, max_length=40):
        """Truncate search query to fit character limit while keeping important info"""
        query = title.replace(" ", "+")

        if len(query) <= max_length:
            return query, title

        words = title.split()

        while len(words) > 1:
            words = words[1:]
            test_title = ' '.join(words)
            test_query = test_title.replace(" ", "+")
            if len(test_query) <= max_length:
                return test_query, test_title

        if len(words) == 1:
            truncated = words[0][:max_length]
            return truncated, truncated

        return query[:max_length], title

    def search_series(self, title, search_type='series'):
        """Search for series on wcostream"""
        query, search_title = self.truncate_search_query(title)

        control.log(f"Searching for series: {query} (length: {len(query)})")

        data = {
            'catara': query,
            'konuara': search_type
        }

        try:
            response = client.request(f'{self._BASE_URL}/search', post=data)
            if not response:
                return []

            soup = BeautifulSoup(response, 'html.parser')

            series_results = []
            series_containers = soup.find_all('div', class_='cerceve')

            for i, container in enumerate(series_containers):
                title_div = container.find('div', class_='aramadabaslik')
                if title_div:
                    link = title_div.find('a')
                    if link:
                        href = link.get('href')
                        title_text = link.get('title') or link.text.strip()

                        if href.startswith('/'):
                            href = href[1:]

                        series_results.append({
                            'index': i,
                            'title': title_text,
                            'href': href,
                            'url': f"{self._BASE_URL}/{href}",
                            'search_used': search_title
                        })

            if series_results:
                control.log(f"Found {len(series_results)} series results")
                return series_results

        except Exception as e:
            control.log(f"Error searching with query '{query}': {e}")

        return []

    def get_episodes_from_series(self, series_url):
        """Get all episodes from a series page"""
        try:
            control.log(f"Getting episodes from: {series_url}")
            response = client.request(series_url)
            if not response:
                return []

            soup = BeautifulSoup(response, 'html.parser')

            episodes = []
            episode_links = soup.find_all('a', href=re.compile(r'episode'))

            for link in episode_links:
                href = link.get('href')
                title_text = link.get('title') or link.text.strip()

                if href and title_text:
                    episodes.append({
                        'title': title_text,
                        'href': href,
                        'url': f"{self._BASE_URL}/{href}" if not href.startswith('http') else href
                    })

            return episodes
        except Exception as e:
            control.log(f"Error getting episodes: {e}")
            return []

    def find_episode_match(self, episodes, target_season, target_episode):
        """Find the matching episode from the episode list"""
        matches = []

        for episode in episodes:
            title_text = episode['title']

            # Pattern 1: Exact season and episode match
            season_episode_pattern = re.compile(rf'season\s+{target_season}\s+episode\s+{target_episode}(?!\d)', re.IGNORECASE)
            if season_episode_pattern.search(title_text):
                episode['match_type'] = 'Perfect Match (Season + Episode)'
                episode['priority'] = 1
                matches.append(episode)
                continue

            # Pattern 2: Episode only match (for shows without clear seasons)
            episode_only_pattern = re.compile(rf'episode\s+{target_episode}(?!\d)', re.IGNORECASE)
            if episode_only_pattern.search(title_text) and not re.search(r'season\s+\d+', title_text, re.IGNORECASE):
                episode['match_type'] = 'Episode Only Match'
                episode['priority'] = 2
                matches.append(episode)
                continue

            # Pattern 3: Contains target episode number (broader match)
            episode_number_pattern = re.compile(rf'\b{target_episode}\b(?!\d)', re.IGNORECASE)
            if episode_number_pattern.search(title_text):
                episode['match_type'] = 'Episode Number Match'
                episode['priority'] = 3
                matches.append(episode)

        # Sort by priority (lower number = higher priority)
        matches.sort(key=lambda x: x['priority'])
        return matches

    def _parse_episode_range(self, range_str):
        """
        Parse episode range string like "1-13" or "13-25"
        Returns tuple (start, end) or None if invalid
        """
        if not range_str or not isinstance(range_str, str):
            return None

        try:
            if '-' in range_str:
                parts = range_str.split('-')
                if len(parts) == 2:
                    start = int(parts[0].strip())
                    end = int(parts[1].strip())
                    return (start, end)
        except ValueError:
            pass

        return None
