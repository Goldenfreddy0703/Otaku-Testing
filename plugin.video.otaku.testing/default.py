# -*- coding: utf-8 -*-
"""
    Otaku Add-on

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# import time
# t0 = time.perf_counter_ns()

import pickle
import service
import json
import ast

from resources.lib import OtakuBrowser
from resources.lib.ui import control, database, utils
from resources.lib.ui.router import Route, router_process
from resources.lib.WatchlistIntegration import add_watchlist

BROWSER = OtakuBrowser.BROWSER

if control.ADDON_VERSION != control.getSetting('version'):
    if control.getInt('showchangelog') == 0:
        service.getChangeLog()
    control.setSetting('version', control.ADDON_VERSION)


def add_last_watched(items):
    mal_id = control.getSetting("addon.last_watched")
    try:
        kodi_meta = pickle.loads(database.get_show(mal_id)['kodi_meta'])
        last_watched = "%s[I]%s[/I]" % (control.lang(30000), kodi_meta['title_userPreferred'])
        info = {
            'UniqueIDs': {
                'mal_id': mal_id,
                **database.get_mapping_ids(mal_id, 'mal_id')
            },
            'title': kodi_meta['title_userPreferred'],
            'plot': kodi_meta['plot'],
            # 'mpaa': kodi_meta[''],
            # 'duration': self.duration_to_seconds(res.get('duration')),
            # 'genre': [x['name'] for x in res.get('genres', [])],
            # 'studio': [x['name'] for x in res.get('studios', [])],
            # 'status': res.get('status'),
            'mediatype': 'tvshow',
            'rating': kodi_meta['rating']
        }
        items.append((last_watched, f'animes/{mal_id}/', kodi_meta['poster'], info))
    except TypeError:
        pass
    return items


@Route('animes/*')
def ANIMES_PAGE(payload, params):
    mal_id, eps_watched = payload.rsplit("/")
    anime_general, content = OtakuBrowser.get_anime_init(mal_id)
    control.draw_items(anime_general, content)


@Route('find_recommendations/*')
def FIND_RECOMMENDATIONS(payload, params):
    path, mal_id, eps_watched = payload.rsplit("/")
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_recommendations(mal_id, page), 'tvshows')


@Route('find_relations/*')
def FIND_RELATIONS(payload, params):
    path, mal_id, eps_watched = payload.rsplit("/")
    control.draw_items(BROWSER.get_relations(mal_id), 'tvshows')


@Route('watch_order/*')
def WATCH_ORDER(payload, params):
    path, mal_id, eps_watched = payload.rsplit("/")
    control.draw_items(BROWSER.get_watch_order(mal_id), 'tvshows')


@Route('airing_calendar')
def AIRING_CALENDAR(payload, params):
    airing = BROWSER.get_airing_calendar()
    from resources.lib.windows.anichart import Anichart

    anime = Anichart('anichart.xml', control.ADDON_PATH, get_anime=OtakuBrowser.get_anime_init, anime_items=airing).doModal()
    if not anime:
        return

    anime, content_type = anime
    control.draw_items(anime, content_type)


@Route('airing_last_season')
def AIRING_LAST_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_airing_last_season(page), 'tvshows')


@Route('airing_this_season')
def AIRING_THIS_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_airing_this_season(page), 'tvshows')


@Route('airing_next_season')
def AIRING_NEXT_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_airing_next_season(page), 'tvshows')


@Route('trending_last_year')
def TRENDING_LAST_YEAR(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_trending_last_year(page), 'tvshows')


@Route('trending_this_year')
def TRENDING_THIS_YEAR(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_trending_this_year(page), 'tvshows')


@Route('trending_last_season')
def TRENDING_LAST_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_trending_last_season(page), 'tvshows')


@Route('trending_this_season')
def TRENDING_THIS_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_trending_this_season(page), 'tvshows')


@Route('all_time_trending')
def ALL_TIME_TRENDING(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_all_time_trending(page), 'tvshows')


@Route('popular_last_year')
def POPULAR_LAST_YEAR(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_popular_last_year(page), 'tvshows')


@Route('popular_this_year')
def POPULAR_THIS_YEAR(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_popular_this_year(page), 'tvshows')


@Route('popular_last_season')
def POPULAR_LAST_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_popular_last_season(page), 'tvshows')


@Route('popular_this_season')
def POPULAR_THIS_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_popular_this_season(page), 'tvshows')


@Route('all_time_popular')
def ALL_TIME_POPULAR(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_all_time_popular(page), 'tvshows')


@Route('voted_last_year')
def VOTED_LAST_YEAR(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_voted_last_year(page), 'tvshows')


@Route('voted_this_year')
def VOTED_THIS_YEAR(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_voted_this_year(page), 'tvshows')


@Route('voted_last_season')
def VOTED_LAST_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_voted_last_season(page), 'tvshows')


@Route('voted_this_season')
def VOTED_THIS_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_voted_this_season(page), 'tvshows')


@Route('all_time_voted')
def ALL_TIME_VOTED(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_all_time_voted(page), 'tvshows')


@Route('favourites_last_year')
def FAVOURITES_LAST_YEAR(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_favourites_last_year(page), 'tvshows')


@Route('favourites_this_year')
def FAVOURITES_THIS_YEAR(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_favourites_this_year(page), 'tvshows')


@Route('favourites_last_season')
def FAVOURITES_LAST_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_favourites_last_season(page), 'tvshows')


@Route('favourites_this_season')
def FAVOURITES_THIS_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_favourites_this_season(page), 'tvshows')


@Route('all_time_favourites')
def ALL_TIME_FAVOURITES(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_all_time_favourites(page), 'tvshows')


@Route('top_100')
def TOP_100(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_top_100(page), 'tvshows')


@Route('genres/*')
def GENRES_PAGES(payload, params):
    genres, tags = payload.rsplit("/")
    page = int(params.get('page', 1))
    if genres or tags:
        control.draw_items(BROWSER.genres_payload(genres, tags, page), 'tvshows')
    else:
        control.draw_items(BROWSER.get_genres(), 'tvshows')


@Route('update_genre_settings')
def UPDATE_GENRE_SETTINGS(payload, params):
    try:
        selected_genres_mal, selected_genres_anilist, selected_tags = BROWSER.update_genre_settings()
    except ValueError:
        return  # Break the code if ValueError occurs

    # Create a dictionary to store the settings
    settings = {
        'selected_genres_mal': selected_genres_mal,
        'selected_genres_anilist': selected_genres_anilist,
        'selected_tags': selected_tags
    }

    # Write the settings to a JSON file
    with open(control.genre_json, 'w') as f:
        json.dump(settings, f)


@Route('genre_action')
def GENRE_ACTION(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_action(page), 'tvshows')


@Route('genre_adventure')
def GENRE_ADVENTURE(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_adventure(page), 'tvshows')


@Route('genre_comedy')
def GENRE_COMEDY(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_comedy(page), 'tvshows')


@Route('genre_drama')
def GENRE_DRAMA(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_drama(page), 'tvshows')


@Route('genre_ecchi')
def GENRE_ECCHI(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_ecchi(page), 'tvshows')


@Route('genre_fantasy')
def GENRE_FANTASY(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_fantasy(page), 'tvshows')


@Route('genre_hentai')
def GENRE_HENTAI(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_hentai(page), 'tvshows')


@Route('genre_horror')
def GENRE_HORROR(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_horror(page), 'tvshows')


@Route('genre_shoujo')
def GENRE_SHOUJO(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_shoujo(page), 'tvshows')


@Route('genre_mecha')
def GENRE_MECHA(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_mecha(page), 'tvshows')


@Route('genre_music')
def GENRE_MUSIC(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_music(page), 'tvshows')


@Route('genre_mystery')
def GENRE_MYSTERY(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_mystery(page), 'tvshows')


@Route('genre_psychological')
def GENRE_PSYCHOLOGICAL(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_psychological(page), 'tvshows')


@Route('genre_romance')
def GENRE_ROMANCE(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_romance(page), 'tvshows')


@Route('genre_sci_fi')
def GENRE_SCI_FI(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_sci_fi(page), 'tvshows')


@Route('genre_slice_of_life')
def GENRE_SLICE_OF_LIFE(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_slice_of_life(page), 'tvshows')


@Route('genre_sports')
def GENRE_SPORTS(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_sports(page), 'tvshows')


@Route('genre_supernatural')
def GENRE_SUPERNATURAL(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_supernatural(page), 'tvshows')


@Route('genre_thriller')
def GENRE_THRILLER(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_genre_thriller(page), 'tvshows')


@Route('search_history')
def SEARCH_HISTORY(payload, params):
    history = database.getSearchHistory('show')
    view_type = 'addons' if control.getBool('interface.content_type') else ''
    if control.getInt('searchhistory') == 0:
        control.draw_items(utils.search_history(history), view_type)
    else:
        SEARCH(payload, params)


@Route('search/*')
def SEARCH(payload, params):
    query = payload
    page = int(params.get('page', 1))
    if not query:
        query = control.keyboard(control.lang(30905))
        if not query:
            return control.draw_items([], 'tvshows')
        if control.getInt('searchhistory') == 0:
            database.addSearchHistory(query, 'show')
    control.draw_items(BROWSER.get_search(query, page), 'tvshows')


@Route('remove_search_item/*')
def REMOVE_SEARCH_ITEM(payload, params):
    if 'search/' in payload:
        search_item = payload.rsplit('search/')[1]
        database.remove_search(table='show', value=search_item)
    control.exit_code()


@Route('edit_search_item/*')
def EDIT_SEARCH_ITEM(payload, params):
    if 'search/' in payload:
        search_item = payload.rsplit('search/')[1]
        if search_item:
            query = control.keyboard(control.lang(30905), search_item)
            if query and query != search_item:
                database.remove_search(table='show', value=search_item)
                database.addSearchHistory(query, 'show')
    control.exit_code()


@Route('play/*')
def PLAY(payload, params):
    mal_id, episode = payload.rsplit("/")
    source_select = bool(params.get('source_select'))
    rescrape = bool(params.get('rescrape'))
    resume_time = params.get('resume')
    if rating := params.get('rating'):
        params['rating'] = ast.literal_eval(rating)
    params['path'] = f"{control.addon_url(f'play/{payload}')}"
    if resume_time:
        resume_time = float(resume_time)
        context = control.context_menu([f'Resume from {utils.format_time(resume_time)}', 'Play from beginning'])
        if context == -1:
            return control.exit_code()
        elif context == 1:
            resume_time = None

    sources = OtakuBrowser.get_sources(mal_id, episode, 'show', rescrape, source_select)
    _mock_args = {"mal_id": mal_id, "episode": episode, 'play': True, 'resume_time': resume_time, 'context': rescrape or source_select, 'params': params}
    if control.getSetting('general.playstyle.episode') == '1' or source_select or rescrape:
        from resources.lib.windows.source_select import SourceSelect
        if control.getSetting('general.dialog') == '5':
            SourceSelect('source_select_az.xml', control.ADDON_PATH, actionArgs=_mock_args, sources=sources, rescrape=rescrape).doModal()
        else:
            SourceSelect('source_select.xml', control.ADDON_PATH, actionArgs=_mock_args, sources=sources, rescrape=rescrape).doModal()
    else:
        from resources.lib.windows.resolver import Resolver
        if control.getSetting('general.dialog') == '5':
            Resolver('resolver_az.xml', control.ADDON_PATH, actionArgs=_mock_args).doModal(sources, {}, False)
        else:
            Resolver('resolver.xml', control.ADDON_PATH, actionArgs=_mock_args).doModal(sources, {}, False)
    control.exit_code()


@Route('play_movie/*')
def PLAY_MOVIE(payload, params):
    mal_id, eps_watched = payload.rsplit("/")
    source_select = bool(params.get('source_select'))
    rescrape = bool(params.get('rescrape'))
    resume_time = params.get('resume')
    params['path'] = f"{control.addon_url(f'play_movie/{payload}')}"
    if resume_time:
        resume_time = float(resume_time)
        context = control.context_menu([f'Resume from {utils.format_time(resume_time)}', 'Play from beginning'])
        if context == -1:
            return
        elif context == 1:
            resume_time = None

    sources = OtakuBrowser.get_sources(mal_id, 1, 'movie', rescrape, source_select)
    _mock_args = {'mal_id': mal_id, 'play': True, 'resume_time': resume_time, 'context': rescrape or source_select, 'params': params}
    if control.getSetting('general.playstyle.movie') == '1' or source_select or rescrape:
        from resources.lib.windows.source_select import SourceSelect
        if control.getSetting('general.dialog') == '5':
            SourceSelect('source_select_az.xml', control.ADDON_PATH, actionArgs=_mock_args, sources=sources, rescrape=rescrape).doModal()
        else:
            SourceSelect('source_select.xml', control.ADDON_PATH, actionArgs=_mock_args, sources=sources, rescrape=rescrape).doModal()
    else:
        from resources.lib.windows.resolver import Resolver
        if control.getSetting('general.dialog') == '5':
            Resolver('resolver_az.xml', control.ADDON_PATH, actionArgs=_mock_args).doModal(sources, {}, False)
        else:
            Resolver('resolver.xml', control.ADDON_PATH, actionArgs=_mock_args).doModal(sources, {}, False)
    control.exit_code()


@Route('marked_as_watched/*')
def MARKED_AS_WATCHED(payload, params):
    from resources.lib.WatchlistFlavor import WatchlistFlavor
    from resources.lib.WatchlistIntegration import watchlist_update_episode

    mal_id, episode = payload.rsplit("/")
    flavor = WatchlistFlavor.get_update_flavor()
    watchlist_update_episode(mal_id, episode)
    control.notify(control.ADDON_NAME, f'Episode #{episode} was Marked as Watched in {flavor.flavor_name}')
    control.execute(f'ActivateWindow(Videos,plugin://{control.ADDON_ID}/watchlist_to_ep/{mal_id}/{episode})')
    control.exit_code()


@Route('delete_anime_database/*')
def DELETE_ANIME_DATABASE(payload, params):
    path, mal_id, eps_watched = payload.rsplit("/")
    database.remove_from_database('shows', mal_id)
    database.remove_from_database('episodes', mal_id)
    database.remove_from_database('show_data', mal_id)
    database.remove_from_database('shows_meta', mal_id)
    control.notify(control.ADDON_NAME, 'Removed from database')
    control.exit_code()


@Route('auth/*')
def AUTH(payload, params):
    if payload == 'realdebrid':
        from resources.lib.debrid.real_debrid import RealDebrid
        RealDebrid().auth()
    elif payload == 'alldebrid':
        from resources.lib.debrid.all_debrid import AllDebrid
        AllDebrid().auth()
    elif payload == 'premiumize':
        from resources.lib.debrid.premiumize import Premiumize
        Premiumize().auth()
    elif payload == 'debridlink':
        from resources.lib.debrid.debrid_link import DebridLink
        DebridLink().auth()
    elif payload == 'torbox':
        from resources.lib.debrid.torbox import TorBox
        TorBox().auth()


@Route('refresh/*')
def REFRESH(payload, params):
    if payload == 'realdebrid':
        from resources.lib.debrid.real_debrid import RealDebrid
        RealDebrid().refreshToken()
    elif payload == 'debridlink':
        from resources.lib.debrid.debrid_link import DebridLink
        DebridLink().refreshToken()
    # elif payload == 'torbox':
    #     from resources.lib.debrid.torbox import TorBox
    #     TorBox().refreshToken()


@Route('fanart_select/*')
def FANART_SELECT(payload, params):
    path, mal_id, eps_watched = payload.rsplit("/")
    if not (episode := database.get_episode(mal_id)):
        OtakuBrowser.get_anime_init(mal_id)
        episode = database.get_episode(mal_id)
    fanart = pickle.loads(episode['kodi_meta'])['image']['fanart'] or []
    fanart_display = fanart + ["None", "Random (Default)"]
    fanart += ["None", ""]
    control.draw_items([utils.allocate_item(f, f'fanart/{mal_id}/{i}', False, False, [], f, {}, fanart=f, landscape=f) for i, f in enumerate(fanart_display)], '')


@Route('fanart/*')
def FANART(payload: str, params: dict):
    mal_id, select = payload.rsplit('/', 1)
    episode = database.get_episode(mal_id)
    fanart = pickle.loads(episode['kodi_meta'])['image']['fanart'] or []
    fanart_display = fanart + ["None", "Random"]
    fanart += ["None", ""]
    fanart_all = control.getStringList(f'fanart.all')
    fanart_all.append(str(mal_id))
    control.setSetting(f'fanart.select.{mal_id}', fanart[int(select)])
    control.setStringList(f'fanart.all', fanart_all)
    control.ok_dialog(control.ADDON_NAME, f"Fanart Set to {fanart_display[int(select)]}")


# ### Menu Items ###
@Route('')
def LIST_MENU(payload, params):
    MENU_ITEMS = [
        (control.lang(30957), "airing_calendar", 'airing_anime_calendar.png', {}),
        (control.lang(30901), "airing_last_season", 'airing_anime.png', {}),
        (control.lang(30902), "airing_this_season", 'airing_anime.png', {}),
        (control.lang(30903), "airing_next_season", 'airing_anime.png', {}),
        # (control.lang(30904), "movies", 'movies.png', {}),
        # (control.lang(30905), "tv_shows", 'tv_shows.png', {}),
        (control.lang(30906), "trending", 'trending.png', {}),
        (control.lang(30907), "popular", 'popular.png', {}),
        (control.lang(30908), "voted", 'voted.png', {}),
        (control.lang(30909), "favourites", 'favourites.png', {}),
        (control.lang(30910), "top_100", 'top_100_anime.png', {}),
        (control.lang(30911), "genres", 'genres_&_tags.png', {}),
        (control.lang(30912), "search_history", 'search.png', {}),
        (control.lang(30913), "tools", 'tools.png', {}),
    ]

    enabled_menu_items = []
    enabled_menu_items = add_watchlist(enabled_menu_items)
    if control.getBool('menu.lastwatched'):
        enabled_menu_items = add_last_watched(enabled_menu_items)
    for i in MENU_ITEMS:
        if control.getBool(i[1]):
            enabled_menu_items.append(i)
    view_type = 'addons' if control.getBool('interface.content_type') else ''
    control.draw_items([utils.allocate_item(name, url, True, False, [], image, info) for name, url, image, info in enabled_menu_items], view_type)


# @Route('movies')
# def MOVIES_MENU(payload, params):
#     MOVIES_ITEMS = [
#         (control.lang(30901), "airing_last_season", 'airing_anime.png', {}),
#         (control.lang(30902), "airing_this_season", 'airing_anime.png', {}),
#         (control.lang(30903), "airing_next_season", 'airing_anime.png', {}),
#         (control.lang(30906), "trending", 'trending.png', {}),
#         (control.lang(30907), "popular", 'popular.png', {}),
#         (control.lang(30908), "voted", 'voted.png', {}),
#         (control.lang(30909), "favourites", 'favourites.png', {}),
#         (control.lang(30910), "top_100", 'top_100_anime.png', {}),
#         (control.lang(30911), "genres", 'genres_&_tags.png', {}),
#         (control.lang(30912), "search_history_movie", 'search.png', {}),
#     ]

#     if control.getBool('menu.lastwatched'):
#         MOVIES_ITEMS = add_last_watched(MOVIES_ITEMS)
#     MOVIES_ITEMS = add_watchlist(MOVIES_ITEMS)
#     # MOVIES_ITEMS = update_menu_paths(MOVIES_ITEMS, 'movies')
#     MOVIES_ITEMS_ = MOVIES_ITEMS[:]
#     for i in MOVIES_ITEMS:
#         if control.getSetting(i[1]) == 'false':
#             MOVIES_ITEMS_.remove(i)
#     control.draw_items([utils.allocate_item(name, url, True, False, [], image, info) for name, url, image, info in MOVIES_ITEMS_])


# @Route('tv_shows')
# def TV_SHOWS_MENU(payload, params):
#     TV_SHOWS_ITEMS = [
#         (control.lang(30901), "airing_last_season", 'airing_anime.png', {}),
#         (control.lang(30902), "airing_this_season", 'airing_anime.png', {}),
#         (control.lang(30903), "airing_next_season", 'airing_anime.png', {}),
#         (control.lang(30906), "trending", 'trending.png', {}),
#         (control.lang(30907), "popular", 'popular.png', {}),
#         (control.lang(30908), "voted", 'voted.png', {}),
#         (control.lang(30909), "favourites", 'favourites.png', {}),
#         (control.lang(30910), "top_100", 'top_100_anime.png', {}),
#         (control.lang(30911), "genres", 'genres_&_tags.png', {}),
#         (control.lang(30912), "search_history_tvshow", 'search.png', {}),
#     ]

#     if control.getBool('menu.lastwatched'):
#         TV_SHOWS_ITEMS = add_last_watched(TV_SHOWS_ITEMS)
#     TV_SHOWS_ITEMS = add_watchlist(TV_SHOWS_ITEMS)
#     # TV_SHOWS_ITEMS = update_menu_paths(TV_SHOWS_ITEMS, 'tv_shows')
#     TV_SHOWS_ITEMS_ = TV_SHOWS_ITEMS[:]
#     for i in TV_SHOWS_ITEMS:
#         if control.getSetting(i[1]) == 'false':
#             TV_SHOWS_ITEMS_.remove(i)
#     control.draw_items([utils.allocate_item(name, url, True, False, [], image, info) for name, url, image, info in TV_SHOWS_ITEMS_])


@Route('trending')
def TRENDING_MENU(payload, params):
    TRENDING_ITEMS = [
        (control.lang(30914), "trending_last_year", 'trending.png', {}),
        (control.lang(30915), "trending_this_year", 'trending.png', {}),
        (control.lang(30916), "trending_last_season", 'trending.png', {}),
        (control.lang(30917), "trending_this_season", 'trending.png', {}),
        (control.lang(30918), "all_time_trending", 'trending.png', {}),
    ]

    enabled_trending_items = []
    for i in TRENDING_ITEMS:
        if control.getBool(i[1]):
            enabled_trending_items.append(i)
    view_type = 'addons' if control.getBool('interface.content_type') else ''
    control.draw_items([utils.allocate_item(name, url, True, False, [], image, info) for name, url, image, info in enabled_trending_items], view_type)


@Route('popular')
def POPULAR_MENU(payload, params):
    POPULAR_ITEMS = [
        (control.lang(30919), "popular_last_year", 'popular.png', {}),
        (control.lang(30920), "popular_this_year", 'popular.png', {}),
        (control.lang(30921), "popular_last_season", 'popular.png', {}),
        (control.lang(30922), "popular_this_season", 'popular.png', {}),
        (control.lang(30923), "all_time_popular", 'popular.png', {}),
    ]

    enabled_popular_items = []
    for i in POPULAR_ITEMS:
        if control.getBool(i[1]):
            enabled_popular_items.append(i)
    view_type = 'addons' if control.getBool('interface.content_type') else ''
    control.draw_items([utils.allocate_item(name, url, True, False, [], image, info) for name, url, image, info in enabled_popular_items], view_type)


@Route('voted')
def VOTED_MENU(payload, params):
    VOTED_ITEMS = [
        (control.lang(30924), "voted_last_year", 'voted.png', {}),
        (control.lang(30925), "voted_this_year", 'voted.png', {}),
        (control.lang(30926), "voted_last_season", 'voted.png', {}),
        (control.lang(30927), "voted_this_season", 'voted.png', {}),
        (control.lang(30928), "all_time_voted", 'voted.png', {}),
    ]

    enabled_voted_items = []
    for i in VOTED_ITEMS:
        if control.getBool(i[1]):
            enabled_voted_items.append(i)
    view_type = 'addons' if control.getBool('interface.content_type') else ''
    control.draw_items([utils.allocate_item(name, url, True, False, [], image, info) for name, url, image, info in enabled_voted_items], view_type)


@Route('favourites')
def FAVOURITES_MENU(payload, params):
    FAVOURITES_ITEMS = [
        (control.lang(30929), "favourites_last_year", 'favourites.png', {}),
        (control.lang(30930), "favourites_this_year", 'favourites.png', {}),
        (control.lang(30931), "favourites_last_season", 'favourites.png', {}),
        (control.lang(30932), "favourites_this_season", 'favourites.png', {}),
        (control.lang(30933), "all_time_favourites", 'favourites.png', {}),
    ]

    enabled_favourites_items = []
    for i in FAVOURITES_ITEMS:
        if control.getBool(i[1]):
            enabled_favourites_items.append(i)
    view_type = 'addons' if control.getBool('interface.content_type') else ''
    control.draw_items([utils.allocate_item(name, url, True, False, [], image, info) for name, url, image, info in enabled_favourites_items], view_type)


@Route('genres')
def GENRES_MENU(payload, params):
    GENRES_ITEMS = [
        (control.lang(30934), "genres//", 'genre_multi.png', {}),
        (control.lang(30935), "genre_action", 'genre_action.png', {}),
        (control.lang(30936), "genre_adventure", 'genre_adventure.png', {}),
        (control.lang(30937), "genre_comedy", 'genre_comedy.png', {}),
        (control.lang(30938), "genre_drama", 'genre_drama.png', {}),
        (control.lang(30939), "genre_ecchi", 'genre_ecchi.png', {}),
        (control.lang(30940), "genre_fantasy", 'genre_fantasy.png', {}),
        (control.lang(30941), "genre_hentai", 'genre_hentai.png', {}),
        (control.lang(30942), "genre_horror", 'genre_horror.png', {}),
        (control.lang(30943), "genre_shoujo", 'genre_shoujo.png', {}),
        (control.lang(30944), "genre_mecha", 'genre_mecha.png', {}),
        (control.lang(30945), "genre_music", 'genre_music.png', {}),
        (control.lang(30946), "genre_mystery", 'genre_mystery.png', {}),
        (control.lang(30947), "genre_psychological", 'genre_psychological.png', {}),
        (control.lang(30948), "genre_romance", 'genre_romance.png', {}),
        (control.lang(30949), "genre_sci_fi", 'genre_sci-fi.png', {}),
        (control.lang(30950), "genre_slice_of_life", 'genre_slice_of_life.png', {}),
        (control.lang(30951), "genre_sports", 'genre_sports.png', {}),
        (control.lang(30952), "genre_supernatural", 'genre_supernatural.png', {}),
        (control.lang(30953), "genre_thriller", 'genre_thriller.png', {}),
    ]

    enabled_genres_items = []
    for i in GENRES_ITEMS:
        if control.getBool(i[1]):
            enabled_genres_items.append(i)
    view_type = 'addons' if control.getBool('interface.content_type') else ''
    control.draw_items([utils.allocate_item(name, url, True, False, [], image, info) for name, url, image, info in enabled_genres_items], view_type)


# @Route('search')
# def SEARCH_MENU(payload, params):
#     SEARCH_ITEMS = [
#         (control.lang(30954), "search_history", 'search.png', {}),
#         (control.lang(30955), "search_history_movie", 'search.png', {}),
#         (control.lang(30956), "search_history_tvshow", 'search.png', {}),
#     ]

#     control.draw_items([utils.allocate_item(name, url, True, False, [], image, info) for name, url, image, info in SEARCH_ITEMS])


@Route('tools')
def TOOLS_MENU(payload, params):
    TOOLS_ITEMS = [
        (control.lang(30010), "change_log", 'changelog.png', {}),
        (control.lang(30011), "settings", 'open_settings_menu.png', {}),
        (control.lang(30012), "clear_cache", 'clear_cache.png', {}),
        (control.lang(30013), "clear_search_history", 'clear_search_history.png', {}),
        (control.lang(30014), "rebuild_database", 'rebuild_database.png', {}),
        (control.lang(30015), "completed_sync", "sync_completed.png", {}),
        (control.lang(30016), 'download_manager', 'download_manager.png', {}),
        (control.lang(30017), 'sort_select', 'sort_select.png', {}),
        (control.lang(30018), 'clear_selected_fanart', 'wipe_addon_data.png', {}),
    ]

    view_type = 'addons' if control.getBool('interface.content_type') else ''
    control.draw_items([utils.allocate_item(name, url, True, False, [], image, info) for name, url, image, info in TOOLS_ITEMS], view_type)


# def update_menu_paths(menu_items, base_path):
#     updated_items = []
#     for name, url, image in menu_items:
#         new_url = f"{base_path}/{url}" if not url.startswith(base_path) else url
#         updated_items.append((name, new_url, image))
#     return updated_items


# ### Maintenance ###
@Route('settings')
def SETTINGS(payload, params):
    control.ADDON.openSettings()


@Route('change_log')
def CHANGE_LOG(payload, params):
    import service
    service.getChangeLog()


@Route('solver_inst')
def SOLVER_INST(payload, params):
    import service
    service.getInstructions()


@Route('clear_cache')
def CLEAR_CACHE(payload, params):
    database.cache_clear()


@Route('clear_search_history')
def CLEAR_SEARCH_HISTORY(payload, params):
    database.clearSearchHistory()
    control.refresh()


@Route('clear_selected_fanart')
def CLEAR_SELECTED_FANART(payload, params):
    silent = False

    if not silent:
        confirm = control.yesno_dialog(control.ADDON_NAME, control.lang(30033))
    if confirm == 0:
        return

    fanart_all = control.getStringList(f'fanart.all')
    for i in fanart_all:
        control.setSetting(f'fanart.select.{i}', '')
    control.setStringList('fanart.all', [])
    if not silent:
        control.notify(f'{control.ADDON_NAME}: Fanart', 'Fanart Successfully Cleared', sound=False)


@Route('rebuild_database')
def REBUILD_DATABASE(payload, params):
    from resources.lib.ui.database_sync import SyncDatabase
    SyncDatabase().re_build_database()


@Route('completed_sync')
def COMPLETED_SYNC(payload, params):
    import service
    service.sync_watchlist()


@Route('sort_select')
def SORT_SELECT(payload, params):
    from resources.lib.windows.sort_select import SortSelect
    SortSelect('sort_select.xml', control.ADDON_PATH).doModal()


# @Route('filter_select')
# def FILTER_SELECT(payload, params):
#     from resources.lib.windows.filter_select import FilterSelect
#     FilterSelect(*('filter_select.xml', control.ADDON_PATH)).doModal()


@Route('download_manager')
def DOWNLOAD_MANAGER(payload, params):
    from resources.lib.windows.download_manager import DownloadManager
    DownloadManager('download_manager.xml', control.ADDON_PATH).doModal()


@Route('import_settings')
def IMPORT_SETTINGS(payload, params):
    import os
    import xbmcvfs

    setting_xml = os.path.join(control.dataPath, 'settings.xml')

    # Import
    import_location = control.browse(1, f"{control.ADDON_NAME}: Import Setting", 'files', 'settings.xml')
    if not import_location:
        return control.exit_code()
    if not import_location.endswith('settings.xml'):
        control.ok_dialog(control.ADDON_NAME, "Invalid File!")
    else:
        yesno = control.yesno_dialog(control.ADDON_NAME, "Are you sure you want to replace settings.xml?")
        if yesno:
            if xbmcvfs.delete(setting_xml) and xbmcvfs.copy(import_location, setting_xml):
                control.ok_dialog(control.ADDON_NAME, "Replaced settings.xml")
            else:
                control.ok_dialog(control.ADDON_NAME, "Could Not Import File!")
    return control.exit_code()


@Route('export_settings')
def EXPORT_SETTINGS(payload, params):
    import os
    import xbmcvfs

    setting_xml = os.path.join(control.dataPath, 'settings.xml')

    # Export
    export_location = control.browse(3, f"{control.ADDON_NAME}: Export Setting", 'files')
    if not export_location:
        control.ok_dialog(control.ADDON_NAME, "Please Select Export Location!")
    else:
        yesno = control.yesno_dialog(control.ADDON_NAME, "Are you sure you want to save settings.xml?")
        if yesno:
            if xbmcvfs.copy(setting_xml, os.path.join(export_location, 'settings.xml')):
                control.ok_dialog(control.ADDON_NAME, "Saved settings.xml")
            else:
                control.ok_dialog(control.ADDON_NAME, "Could Not Export File!")
    return control.exit_code()


@Route('toggleLanguageInvoker')
def TOGGLE_LANGUAGE_INVOKER(payload, params):
    import service
    service.toggle_reuselanguageinvoker()


@Route('inputstreamadaptive')
def INPUTSTREAMADAPTIVE(payload, params):
    import xbmcaddon
    try:
        xbmcaddon.Addon('inputstream.adaptive').openSettings()
    except RuntimeError:
        control.notify(control.ADDON_NAME, "InputStream Adaptive is not installed.")


@Route('inputstreamhelper')
def INPUTSTREAMHELPER(payload, params):
    import xbmcaddon
    try:
        xbmcaddon.Addon('inputstream.adaptive')
        control.ok_dialog(control.ADDON_NAME, "InputStream Adaptive is already installed.")
    except RuntimeError:
        xbmc.executebuiltin('InstallAddon(inputstream.adaptive)')


@Route('trakt_settings')
def TRAKT_SETTINGS(payload, params):
    import xbmcaddon
    try:
        xbmcaddon.Addon('script.trakt').openSettings()
    except RuntimeError:
        control.notify(control.ADDON_NAME, "Trakt Script is not installed.")


@Route('trakt_script')
def TRAKT_SCRIPT(payload, params):
    import xbmcaddon
    try:
        xbmcaddon.Addon('script.trakt')
        control.ok_dialog(control.ADDON_NAME, "Trakt Script is already installed.")
    except RuntimeError:
        xbmc.executebuiltin('InstallAddon(script.trakt)')


if __name__ == "__main__":
    plugin_url = control.get_plugin_url()
    plugin_params = control.get_plugin_params()
    router_process(plugin_url, plugin_params)
    if len(control.playList) > 0:
        import xbmc
        if not xbmc.Player().isPlaying():
            control.playList.clear()

# t1 = time.perf_counter_ns()
# totaltime = (t1-t0)/1_000_000
# control.print(totaltime, 'ms')
