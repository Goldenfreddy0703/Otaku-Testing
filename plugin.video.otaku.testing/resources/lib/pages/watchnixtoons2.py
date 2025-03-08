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
    _BASE_URL = 'https://www.wcofun.net/'

    def get_sources(self, mal_id, episode):
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        title = kodi_meta.get('name')
        clean_title = self._clean_title(title)
    
        control.print(title, clean_title, mal_id, episode)
        source_setting = control.getSetting('general.source').lower()
        sources = []
    
        if source_setting == "both":
            # Process subbed list
            sub_list = self.fetch_anime_list_by_type("sub")
            control.print("Subbed list:", sub_list)
            if sub_list:
                names_query = ','.join([item['name'] for item in sub_list])
                fuzzy_resp = client.request('https://armkai.vercel.app/api/fuzzypacks',
                                            params={"dict": names_query, "match": clean_title})
                try:
                    indices = json.loads(fuzzy_resp)
                except Exception:
                    indices = []
                if indices:
                    best_index = indices[0]
                    matched_anime = sub_list[best_index]
                    sources.extend(self.parse_sources_from_anime_page(matched_anime['url'], episode))
            
            # Process dubbed list
            dub_list = self.fetch_anime_list_by_type("dub")
            control.print("Dubbed list:", dub_list)
            if dub_list:
                names_query = ','.join([item['name'] for item in dub_list])
                fuzzy_resp = client.request('https://armkai.vercel.app/api/fuzzypacks',
                                            params={"dict": names_query, "match": clean_title})
                try:
                    indices = json.loads(fuzzy_resp)
                except Exception:
                    indices = []
                if indices:
                    best_index = indices[0]
                    matched_anime = dub_list[best_index]
                    sources.extend(self.parse_sources_from_anime_page(matched_anime['url'], episode))
        else:
            # Use the default list based on the user's setting ("sub" or "dub")
            anime_list = self.fetch_anime_list_by_type(source_setting)
            control.print(anime_list)
            if not anime_list:
                return []
            names_query = ','.join([item['name'] for item in anime_list])
            fuzzy_resp = client.request('https://armkai.vercel.app/api/fuzzypacks',
                                        params={"dict": names_query, "match": clean_title})
            try:
                indices = json.loads(fuzzy_resp)
            except Exception:
                indices = []
            if indices:
                best_index = indices[0]
                matched_anime = anime_list[best_index]
                sources = self.parse_sources_from_anime_page(matched_anime['url'], episode)
        
        return sources
    
    
    def fetch_anime_list_by_type(self, list_type):
        """
        Retrieve and parse the list of anime from the website for a specific type:
        "dub" or "sub". If list_type is "sub" (or any value other than "dub"),
        we use the subbed anime list.
        """
        if list_type == 'dub':
            url = urllib.parse.urljoin(self._BASE_URL, "dubbed-anime-list")
        else:
            url = urllib.parse.urljoin(self._BASE_URL, "subbed-anime-list")
        
        control.print(url)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            control.print("Error fetching URL:", str(e))
            return []
        
        control.print(html)
        soup = BeautifulSoup(html, "html.parser")
        anime_items = [a for a in soup.find_all('a', href=True) if a['href'].startswith("/anime/")]
        
        anime_list = []
        for item in anime_items:
            name = item.get_text().strip()
            link = urllib.parse.urljoin(self._BASE_URL, item['href'])
            if name:
                anime_list.append({'name': self._clean_title(name), 'url': link})
        return anime_list
    
    def parse_sources_from_anime_page(self, anime_url, episode):
        """
        Given the URL of a specific anime page on WCO, retrieve the page and filter the episode links.
        This sample looks for containers with class "cat-eps" and checks if the text holds the episode number
        along with one of the keywords for subtitles or dubbing.
        """
        response = client.request(anime_url)
        if not response:
            return []
        soup = BeautifulSoup(response, "html.parser")
        
        # Get the user's preference from the general.source setting (sub/dub/both)
        source_pref = control.getSetting('general.source').lower()
        
        # Look for all episode link containers (example from page source: class "cat-eps")
        episode_items = soup.find_all("div", class_="cat-eps")
        matching_url = None
        for container in episode_items:
            a_tag = container.find("a", href=True)
            if not a_tag:
                continue
            link_text = a_tag.get_text().lower()
            # Check if the link pertains to the requested episode number.
            # For example, expect "episode 12" inside the text.
            if f"episode {episode}" in link_text:
                # If the user wants only subbed or dubbed, enforce that here.
                if source_pref == "dub" and not any(kw in link_text for kw in ["dub", "dubbed"]):
                    continue
                if source_pref == "sub" and not any(kw in link_text for kw in ["sub", "subbed"]):
                    continue
                matching_url = urllib.parse.urljoin(anime_url, a_tag["href"])
                break
    
        if not matching_url:
            control.print("No matching episode found for episode", episode)
            return []
    
        # Create a source dict for the matching episode URL
        source = {
            'release_title': f'{self._clean_title(matching_url)} - Episode {episode}',
            'hash': matching_url,
            'type': 'embed',
            'quality': 0,
            'debrid_provider': '',
            'provider': 'watchnixtoons2',
            'size': 'NA',
            'seeders': 0,
            'byte_size': 0,
            'info': [],
            # You can tailor language flag based on keyword in the link:
            'lang': 3 if "dub" in matching_url.lower() else 2,
            'channel': 3,
            'sub': 1
        }
        return [source]