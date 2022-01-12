import logging
import json
from core.bgg_suggestions import BggSuggestions
from core.bgg_exceptions import BggSuggestionException
from telegram.ext import CommandHandler, MessageHandler, Filters, ConversationHandler, Updater

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = json.load(open("resources/telegram_token.json"))['TOKEN']
CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)
START_MESSAGE = "Hi! Start getting suggestions or use the /help command for further details"
HOW_TO_USE_IT = """🧪In order to test it, just use the /username command and follow the instructions.
🎴We also offer a single-boardgame-based version of the suggestions, use the /boardgame command to test it"""
HELP_MESSAGE = f"""Hi and welcome in this BGG games suggestion system.

🧠The idea behind these suggestions is explained [here](https://github.com/informatica92/BGG-suggestions)

❓ In a nutshell:
1. you send us your BGG username
2. we analyze your boardgames collection
3. then we do the same with the [hotness](https://boardgamegeek.com/hotness)
4. we cross-check both the results
5. we return the top 5 games that fit the most

{HOW_TO_USE_IT}
"""


def start_command(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text(START_MESSAGE)


def help_command(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')


def suggest_from_username(update, context):
    """Suggest boardgames to the username."""
    username = update.message.text
    update.message.reply_text("A list of suggestion according to your BGG collection is coming...")
    logger.info(f"get suggestions for user '{username}'")
    try:
        suggestions = bgg_suggestions.suggest_from_user(username=username, format_="text")
        for suggestion in suggestions:
            update.message.reply_text(suggestion)
    except BggSuggestionException as e:
        update.message.reply_text(str(e))
        return CHOOSING
    except (BaseException, ValueError) as e:
        update.message.reply_text("Generic error occurred")
        raise e

    return ConversationHandler.END


def suggest_from_boardgame(update, context):
    """Suggest boardgames to the username."""
    boardgame = update.message.text
    update.message.reply_text("A list of suggestion according to this boardgame is coming...")
    logger.info(f"get suggestions for boardgame '{boardgame}'")
    # TODO
    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def simple():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("help", help_command))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, suggest_from_username))

    # log all errors
    # dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def ask_for_username(update, context):
    update.message.reply_text(
        "Just type your BGG username.\n"
        "EG: if your username is 'test001', just send it here and wait for the results"
    )
    return CHOOSING


def ask_for_boardgame_name(update, context):
    update.message.reply_text(
        "NOT IMPLEMENTED YET."
    )
    return ConversationHandler.END


def fallback_action(update, context):
    update.message.reply_text(HOW_TO_USE_IT)


def conversation():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("help", help_command))

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_username_handler = ConversationHandler(
        entry_points=[CommandHandler('username', ask_for_username)],
        states={CHOOSING: [MessageHandler(Filters.text, suggest_from_username)]},
        fallbacks=[]
    )

    conv_boardgame_handler = ConversationHandler(
        entry_points=[CommandHandler('boardgame', ask_for_boardgame_name)],
        states={CHOOSING: [MessageHandler(Filters.text, suggest_from_boardgame)]},
        fallbacks=[]
    )

    dp.add_handler(conv_username_handler)
    dp.add_handler(conv_boardgame_handler)

    # on non-command
    dp.add_handler(MessageHandler(Filters.text, fallback_action))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    bgg_suggestions = BggSuggestions()
    # simple()
    conversation()
