from apscheduler.schedulers.background import BackgroundScheduler
import logging
import pandas as pd
import numpy as np
from core.bgg_api_manager import load_hot_boardgames, load_user_collection, get_boardgame_features


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
        liked_boardgames_df = pd.DataFrame(
            [
                {
                    'id': boardgame_id,
                    'name': boardgame_name,
                    'features': get_boardgame_features(boardgame_id),
                    'numplays': 0
                }
            ]
        )

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

    def _get_ranked(self, liked_boardgames_df: pd.DataFrame):
        # merge the two DFs hot_boardgames_df and liked_boardgames_df in a cross join way => each hot bg with every
        # liked bg in this way we are ready to calculate the affinity for each couple of boardgames
        total_df = self.hot_boardgames_df.merge(liked_boardgames_df, how='cross', suffixes=('_hot', '_liked'))

        # calculate now the affinity for each couple hot_boardgame - liked_boardgame and add to the total_df
        # the corresponding affinity and common features that contributed to obtain that affinity
        total_df[['affinity', 'comm_features']] = total_df.apply(self.calculate_affinity, result_type='expand', axis=1)

        ranked_df = BggSuggestions.affinity_handler(total_df, mode='sum_weighted')

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
                    f"https://boardgamegeek.com/boardgame/{el['id_hot']} \n"
                s += "because you also like:"
                for o in el['because_you_also_like']:
                    s += f"\n - '_{o[0]}_' with "
                    for cf in o[1][0:3]:
                        s += f"{cf}, "
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
    def affinity_handler(total_df, mode=None):
        if mode not in ['max', 'sum_weighted']:
            raise AttributeError(f"mode '{mode}' not in allowed ones: {['max', 'sum_weighted']}")

        if mode == 'max':
            total_df['because_you_also_like'] = total_df.apply(
                lambda x: (x['name_liked'], x['comm_features'], x['affinity']),
                axis=1
            )

            ranked_df = total_df.query(f"name_hot not in {list(total_df.name_liked.unique())}") \
                .groupby(["id_hot", "name_hot", "thumbnail", "description"]) \
                .agg(
                    {
                        'affinity': max,
                        'because_you_also_like': lambda x: sorted(list(x), key=lambda x: x[2], reverse=True)[:1]
                    }, result_type='expand') \
                .reset_index() \
                .rename({'affinity': 'total_affinity'}, axis=1)
        elif mode == 'sum_weighted':
            total_df['weighted_affinity'] = total_df['affinity'] * (total_df['numplays'] + 0.5)
            total_df['because_you_also_like'] = total_df.apply(
                lambda x: (x['name_liked'], x['comm_features'], x['weighted_affinity']),
                axis=1
            )

            ranked_df = total_df.query(f"name_hot not in {list(total_df.name_liked.unique())}") \
                .groupby(["id_hot", "name_hot", "thumbnail", "description"]) \
                .agg(
                    {
                        'weighted_affinity': sum,
                        'because_you_also_like': lambda x: sorted(list(x), key=lambda x: x[2], reverse=True)[:3]
                    }, result_type='expand') \
                .reset_index() \
                .rename({'weighted_affinity': 'total_affinity'}, axis=1) \

        return ranked_df.sort_values('total_affinity', ascending=False, ignore_index=True)
