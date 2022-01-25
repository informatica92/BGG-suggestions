from apscheduler.schedulers.background import BackgroundScheduler
import logging
import pandas as pd
from core.bgg_api_manager import load_hot_boardgames, load_user_collection, get_boardgame_features, item_to_dict, \
    check_hotness


TOP_N = 5

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
scheduler.start()

scheduler.add_job(load_hot_boardgames, 'interval', minutes=60)
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)


class BggSuggestions(object):
    def __init__(self):
        # get hot boardgames
        self.hot_boardgames_df = pd.DataFrame(load_hot_boardgames())
        self.filters = ["own", "want", "wanttoplay", "wanttobuy", "wishlist", "preordered"]

    def suggest_from_boardgame(self, boardgame_id, top_n=5, format_='dict'):
        _, (boardgame_name) = get_boardgame_features(boardgame_id, additional_info=['name'])
        features = get_boardgame_features(boardgame_id)
        numplays = 0
        liked_boardgames_df = pd.DataFrame([item_to_dict(boardgame_id, boardgame_name, features, numplays)])

        # calculate the hotness ranking according to the user's liked board games
        ranked_df = self._get_ranked(liked_boardgames_df)

        # format result according to the TOP N and the desired format
        result = BggSuggestions._get_top_n(ranked_df, n=top_n, format_=format_)

        return result

    def suggest_from_user(self, username, top_n=5, format_='dict'):
        # get user's collection.
        liked_boardgames_df = pd.DataFrame(load_user_collection(username, filters=self.filters))

        # calculate the hotness ranking according to the user's liked board games
        ranked_df = self._get_ranked(liked_boardgames_df)

        # format result according to the TOP N and the desired format
        result = BggSuggestions._get_top_n(ranked_df, n=top_n, format_=format_)

        return result

    def _get_ranked(self, liked_boardgames_df: pd.DataFrame, mode='sum_weighted'):
        # check if hotness list is ok
        check_hotness()

        # merge the two DFs hot_boardgames_df and liked_boardgames_df in a cross join way => each hot bg with every
        # liked bg in this way we are ready to calculate the affinity for each couple of boardgames
        total_df = self.hot_boardgames_df.merge(liked_boardgames_df, how='cross', suffixes=('_hot', '_liked'))

        # calculate now the affinity for each couple hot_boardgame - liked_boardgame and add to the total_df
        # the corresponding affinity and common features that contributed to obtain that affinity
        total_df[['affinity', 'comm_features']] = total_df.apply(self.calculate_affinity, result_type='expand', axis=1)

        # convert total_df dataframe into ranked_df according to the mode (max, sum of weighted...)
        ranked_df = BggSuggestions.affinity_handler(total_df, mode=mode)

        return ranked_df

    @staticmethod
    def _get_top_n(suggestions, n=5, format_='dict'):
        base = suggestions.head(n).reset_index(drop=False)
        if format_ == 'dict':
            return base.to_dict(orient='records')
        if format_ == 'dataframe':
            return base
        if format_ == 'markdown':
            def text_format(el):
                s = f"*{el['name_hot']}* ({el['total_affinity']:.2f}) \n" \
                    f"🔗 https://boardgamegeek.com/boardgame/{el['id_hot']} \n"
                s += "❤ because you also like:"
                for o in el['because_you_also_like']:
                    s += f"\n - '_{o[0]}_' ({float(o[2]):.2f}) with "
                    for cf in o[1][0:3]:
                        s += f"{cf}, "
                    s += "..."
                s += "..."
                return s
            return [text_format(el) for el in BggSuggestions._get_top_n(suggestions, n=n, format_='dict')]
        else:
            raise AttributeError("unexpected value for attribute 'format_'")

    # CORE
    # the affinity calculation is based on the following idea: calculate the percentage of the features
    # of each hottest game compared against each game the user likes
    @staticmethod
    def calculate_affinity(x):
        hot_boardgame, liked_boardgame = x['features_hot'], x['features_liked']
        n_features = 0
        common_features = []
        liked_boardgame_features_id = [f['value'] for f in liked_boardgame]
        for hot_boardgame_feature in hot_boardgame:
            n_features += 1
            if hot_boardgame_feature['value'] in liked_boardgame_features_id:
                common_features.append(hot_boardgame_feature['value'])
        if n_features > 0:
            affinity = len(common_features) / n_features
        else:
            affinity = 0
        return affinity, common_features

    @staticmethod
    def affinity_handler(df, mode=None):
        if mode not in ['max', 'sum_weighted']:
            raise AttributeError(f"mode '{mode}' not in allowed ones: {['max', 'sum_weighted']}")

        affinity_col, operation, first_n = None, None, None
        if mode == 'max':
            # MAX OF THE RAW AFFINITY
            affinity_col = 'affinity'
            operation = max
            first_n = 1
        elif mode == 'sum_weighted':
            # SUM OF THE AFFINITY BY NUMPLAYS
            df['weighted_affinity'] = df['affinity'] * (df['numplays'] + 0.5)
            affinity_col = 'weighted_affinity'
            operation = sum
            first_n = 3

        # DEFINE THE 'because_you_also_like' COLUMN CONCATENATING 'name_liked', 'comm_features' and the affinity_col
        df['because_you_also_like'] = df.apply(lambda x: (x['name_liked'], x['comm_features'], x[affinity_col]), axis=1)

        # CREATE THE ranked_df DATAFRAME AS...
        # 1. FILTER OUT THE LIKED BOARD GAMES
        # 2. GROUP BY "id_hot", "name_hot", "thumbnail", "description"
        # 3. CALCULATE THE operation ON THE affinity_col (eg: max on affinity)
        # 4. CALCULATE THE because_you_also_like LIST OF THE first_n BOARD GAMES ORDERED BY AFFINITY (DESCENDANT)
        # 5. RESET INDEX
        # 6. RENAME affinity_col IN 'total_affinity'
        # FINAL DF ALWAYS HAS: id_hot, name_hot, thumbnail, description, total_affinity, because_you_also_like
        ranked_df = df.query(f"name_hot not in {list(df.name_liked.unique())}") \
            .groupby(["id_hot", "name_hot", "thumbnail", "description"]) \
            .agg(
                {
                    affinity_col: operation,
                    'because_you_also_like': lambda x: sorted(list(x), key=lambda k: k[2], reverse=True)[:first_n]
                },
                result_type='expand') \
            .reset_index() \
            .rename({affinity_col: 'total_affinity'}, axis=1)

        # FINAL SORTING
        return ranked_df.sort_values('total_affinity', ascending=False, ignore_index=True)
