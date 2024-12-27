import re

from bs4 import BeautifulSoup
from resources.lib.ui import client

url = "https://www.animefillerlist.com/shows"


def get_data(anime_eng_title):
    filler_list = []
    if anime_eng_title:
        anime_url = re.sub(r'\W', '-', anime_eng_title)
        try:
            response = client.request(f'{url}/{anime_url}')
            if response:
                soup = BeautifulSoup(response, 'html.parser')
                soup_all = soup.find('table', class_="EpisodeList").tbody.find_all('tr')
                filler_list = [i.span.text for i in soup_all]
        except AttributeError:
            pass

    return filler_list
