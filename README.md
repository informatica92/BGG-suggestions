# BGG-suggestions
The board games world is absolutely wide: every day a new product is released or is launched on Kickstarter or receives a digital versions...

For all these reasons and many others, is quite difficult to keep an eye on the board games that can suit us and doing this by hand, can become a huge waste of time checking online pages, rulebooks or YouTube videos.

Here, this little repository comes to help everyone.

Starting from everyone's BGG collection, it makes an analysis of each game we own and want to buy or play and cross-check these games with the BGG hotness.

## What is BGG?
If you don't know what BGG is, it stands for "BoardGameGeek" and it is a global board games encyclopedia where you can find any board game (and not only, it also works with rpg, expansions...) checking its mechanisms, which kind of game it is, who created it, photos, reviews...

On this site you can also manage a personal collection of games you own, want to play, want to buy.

Finally, BGG also manages a hotness page where the most important games of the moment are included, and it is continuously updated with a ranking (from 1 to 50).

**The idea behind this repository is to suggest some of the hottest BGG boardgame according the features of the games each user already added to their collection on the same platform**

## How these suggestions works
### The telegram bot
First, in order to allow many users to have access to this system, we decided to host it as a Telegram bot.

A telegram bot is just a chat like any other where you can send commands in order to make the bot execute some actiosn.

You can find the bot looking for '@notifyme_regexmatch_bot'

After the initial /start command, you can take a look at the /help command results to see how it works

### The suggestions
Everywhere we surf on the internet, we are surrounded by recommendations, tailored results... and all these tips are based on specific algorithms that require a big and complete dataset.

BGG doesn't offer this kind of access to its database, so no bulk extractions, but it has a complete and fast XML API system that can work for our purposes.

What we have here, in fact, is a very simple recommendations system based on the number of features shared between the users' collection board games and the hotness ones.

#### The features
On each board game on BGG just below the initial part, you can find a list of characteristics belonging to different fields: Type, Category, Mechanisms and Family.

![features](.\resources\images\features_1.PNG "features")

Theoretically,the more features two board games shares, the more similar they are and if we appreciated the first one, very likely we can be interested in the second as well.

A graphic explanation of what we just said can be found in the image below:

![common_features](.\resources\images\common_features.png "common features")

In this case, these 2 board games share the 33.33% of the features, or, in other words, an affinity equal to 0.33

### The results
This being said, it's pretty easy to guess how our suggestion system works:
1. We use the BGG APIs to get the hotness list
![hotness](.\resources\images\hotness.PNG "hotness")
2. We use the BGG APIs to get the user collection
![collection](.\resources\images\collection.PNG "collection")
3. We calculate the affinity, as described above, between each hotness game and each user's collection game
![cross_affinity](.\resources\images\cross_affinity.PNG "cross_affinity")
4. For each hotness game we identify the MAX affinity value obtained and boardgame(s) that generated that value
![max_affinity](.\resources\images\max_affinity.PNG "max_affinity")
5. We finally rank the hotness games by their max value of affinity, and we select the top 5
![results](.\resources\images\results.PNG "results")


