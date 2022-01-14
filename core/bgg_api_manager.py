from bs4 import BeautifulSoup as bs
import requests
from time import sleep
import logging
import cachetools
from core.bgg_exceptions import BggSuggestionException


HOT_BOARDGAME_URL = "https://www.boardgamegeek.com/xmlapi2/hot?type=boardgame"
BOARDGAME_INFO_URL = "https://www.boardgamegeek.com/xmlapi2/thing?id={id}"
USER_COLLECTION_URL = "https://www.boardgamegeek.com/xmlapi2/collection?username={username}"
SEARCH_URL = "https://boardgamegeek.com/xmlapi2/search?type=boardgame&query={query}"  # expansions are included into 'boardgame' type

ALLOWED_FILTERS = ["own", "prevowned", "fortrade", "want", "wanttoplay", "wanttobuy", "wishlist", "preordered"]


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

hotness_ttl_cache = cachetools.TTLCache(ttl=60*60*1, maxsize=1)  # 1 hour
collection_ttl_cache = cachetools.TTLCache(ttl=60*60*1, maxsize=10)  # 1 hour


# simple function for requests execution and BeautifulSoup content conversion
def get_bs_content_from_url(url):
    url_response = requests.get(url)
    url_bs_content = bs(url_response.content, "lxml")
    return url_bs_content


# simple function that, given an id, it returns its features (boardgamecategory, boardgamemechanic...)
def get_boardgame_features(id_, additional_info=None):
    if additional_info is None:
        additional_info = []
    features = []
    boardgame_info_response_bs_content = get_bs_content_from_url(BOARDGAME_INFO_URL.format(id=id_))
    links = boardgame_info_response_bs_content.find_all("link")
    for link in links:
        features.append(
            {
                "type": link.get("type"),
                "id": link.get("id"),
                "value": link.get("value")
            }
        )
    if len(additional_info) == 0:
        return features
    else:
        addition_info_array = []
        for a in additional_info:
            info = boardgame_info_response_bs_content.find(a)
            if info is not None:
                addition_info_array.append(info.text)
            else:
                addition_info_array.append(None)
        return features, *addition_info_array


def search_boardgame(boardgame_name, raise_if_empty=True):
    search_results_bs_content = get_bs_content_from_url(SEARCH_URL.format(query=boardgame_name))
    items = search_results_bs_content.find_all("item")
    results = [
        {
            'id': i.get("id"),
            'name': i.find("name").get("value"),
            'year': i.find("yearpublished").get("value")
        } for i in items
    ]
    if raise_if_empty and len(results) == 0:
        raise BggSuggestionException("Empty results, try another string")
    return results


def load_hot_boardgames():
    hot_boardgames = hotness_ttl_cache.get('hot_boardgames', [])

    if len(hot_boardgames) == 0:
        logger.info("updating hot_boardgames cache")
        hot_boardgames_bs_content = get_bs_content_from_url(HOT_BOARDGAME_URL)
        items = hot_boardgames_bs_content.find_all("item")
        for item in items:
            features, description, thumbnail = get_boardgame_features(
                item.get("id"),
                additional_info=['description', 'thumbnail']
            )
            hot_boardgames.append(
                {
                    "id": item.get("id"),
                    "rank": item.get("id"),
                    "name": item.find("name").get("value"),
                    "features": features,
                    "description": description,
                    "thumbnail": thumbnail
                }
            )

        hotness_ttl_cache['hot_boardgames'] = hot_boardgames
    return hot_boardgames


def load_user_collection(username, filters=None):
    # Please note that for the first request, you only get a "got it, retry later" response
    # so if this is the case, retry again after 5s
    # since the user collection is pretty static during the day, add the result into a TTL cache
    # of five elements and 12h of life
    if filters is None:
        filters = ["own", "prevowned", "fortrade", "want", "wanttoplay", "wanttobuy", "wishlist", "preordered"]
    if set(filters) - set(ALLOWED_FILTERS):  # A - B
        raise AttributeError(f"unexpected filter {list(set(filters) - set(ALLOWED_FILTERS))}")
    liked_boardgames = collection_ttl_cache.get(username, [])

    if len(liked_boardgames) == 0:
        logger.info("updating users collections")
        collection_bs_content = get_bs_content_from_url(USER_COLLECTION_URL.format(username=username))
        if collection_bs_content.find("errors"):
            raise BggSuggestionException(f"👤⛔ Username '{username}' not found")
        liked_items = collection_bs_content.find_all("item")
        if len(liked_items) == 0:
            sleep(5)
            collection_bs_content = get_bs_content_from_url(USER_COLLECTION_URL.format(username=username))
            liked_items = collection_bs_content.find_all("item")

        # for each boardgame in collection, get the same features we got above for the hottest
        logger.info(f"found {len(liked_items)} liked boardgames, processing...")
        for liked_item in liked_items:
            status = liked_item.find('status')
            # logger.info(status)
            to_include = sum([int(status.get(f)) for f in filters])
            if to_include > 0:
                liked_boardgames.append(
                    {
                        "id": liked_item.get("objectid"),
                        "name": liked_item.find("name").text,
                        "features": get_boardgame_features(liked_item.get("objectid"))
                    }
                )
            else:
                logger.info(f"EXCLUDING {liked_item.find('name').text}")
        collection_ttl_cache[username] = liked_boardgames

    # if the number of liked boardgames is empty makes no sense to continue but this can be caused by:
    # - the user doesn't have any boardgame in their collection, try with another username you know it has a
    # not-empty collection
    # - the user has a big collection, try again later because it may take a while to get it in this 2-steps process
    if len(liked_boardgames) == 0:
        raise BggSuggestionException(f"""📜⛔ No liked boardgame for user '{username}'. This can be caused by:
- no boardgame in the collection, try another username
- user has a big collection, try later
                """)
    return liked_boardgames
