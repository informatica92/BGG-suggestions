class EnglishStrings(object):
    START_MESSAGE = "Hi! Start getting suggestions or use the /help command for further details"
    HOW_TO_USE_IT = "🧪In order to test it, just use the /username command and follow the instructions.\n" \
                    "🎴We also offer a single-boardgame-based version of the suggestions, use the /boardgame command " \
                    "to test it"""
    HELP_MESSAGE = f"Hi and welcome in this BGG games suggestion system.\n" \
                   f"\n" \
                   f"🧠The idea behind these suggestions is well explained on " \
                   f"[GitHub](https://github.com/informatica92/BGG-suggestions)\n" \
                   f"\n" \
                   f"❓ In a nutshell:\n" \
                   f"1. you send us your BGG username\n" \
                   f"2. we analyze your boardgames collection\n" \
                   f"NB: only 'own', 'want to play', 'want to buy'...\n" \
                   f"3. then we do the same with the [hotness](https://boardgamegeek.com/hotness)\n" \
                   f"4. we cross-check both the results\n" \
                   f"5. we return the top 5 games that fit the most\n" \
                   f"\n" \
                   f"{HOW_TO_USE_IT}"
    ASK_FOR_USERNAME = "📝 Ok, tell me your BGG username\n" \
                       "EG: if your username is 'test001', just send it as it is"
    ASK_FOR_BOARDGAME_NAME = "📝 Ok, tell me the name of the boardgame\n" \
                             "EG: if you want to get suggestions related to 'Takenoko', just send it"
    INTRO_MESSAGE = "⌛ A list of suggestion related to {thing} is coming..."
    OPTION = '🔀 Which one of these are you referring at?'
