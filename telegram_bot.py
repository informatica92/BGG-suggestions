# ADD collection analysis: preferred mechanic, most played games...

import logging
import json
from core.bgg_suggestions import BggSuggestions
from core.bgg_api_manager import search_boardgame
from core.bgg_exceptions import BggSuggestionException
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, MessageHandler, Filters, ConversationHandler, Updater, CallbackQueryHandler
from telegram_resources.strings import EnglishStrings as language

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = json.load(open("resources/telegram_token.json"))['TOKEN']
CHOOSING, TYPING_CHOICE = range(2)


def start_command(update: Update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text(language.START_MESSAGE)


def help_command(update: Update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text(language.HELP_MESSAGE, parse_mode='Markdown', disable_web_page_preview=True)


def suggest_from_username(update: Update, context):
    """Suggest boardgames to the username."""
    username = update.message.text
    update.message.reply_text(language.INTRO_MESSAGE.format(thing=f"{username}'s BGG collection"))
    logger.info(f"get suggestions for user '{username}'")
    try:
        suggestions = bgg_suggestions.suggest_from_user(username=username, format_="markdown")
        for suggestion in suggestions:
            update.message.reply_text(suggestion, parse_mode='Markdown')
    except BggSuggestionException as e:
        update.message.reply_text(str(e))
        return CHOOSING
    except (BaseException, ValueError) as e:
        update.message.reply_text("Generic error occurred")
        raise e

    return ConversationHandler.END


def suggest_from_boardgame(update: Update, context):
    """Suggest boardgames to the username."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    boardgame_id = int(query.data)
    try:
        suggestions = bgg_suggestions.suggest_from_boardgame(boardgame_id, format_="markdown")
        for suggestion in suggestions:
            query.message.reply_text(suggestion, parse_mode='Markdown')
            # update.message.reply_text(suggestion)
    except BggSuggestionException as e:
        update.message.reply_text(str(e))
        return CHOOSING
    except (BaseException, ValueError) as e:
        update.message.reply_text("Generic error occurred")
        raise e

    return ConversationHandler.END


def error(update: Update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def ask_for_username(update: Update, context):
    update.message.reply_text(language.ASK_FOR_USERNAME)
    return CHOOSING


def ask_for_boardgame_name(update: Update, context):
    update.message.reply_text(language.ASK_FOR_BOARDGAME_NAME)
    return CHOOSING


def boardgame_selection_from_name(update: Update, context):
    boardgame = update.message.text
    update.message.reply_text(language.INTRO_MESSAGE.format(thing=str(boardgame).capitalize()))
    logger.info(f"get suggestions for boardgame '{boardgame}'")
    try:
        results = search_boardgame(boardgame)
        keyboard = [
            [InlineKeyboardButton(f"{r['name']} ({r['year']})", callback_data=r['id'])] for r in results
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(language.OPTION, reply_markup=reply_markup)
    except BggSuggestionException as e:
        update.message.reply_text(str(e))
        return CHOOSING
    except (BaseException, ValueError) as e:
        update.message.reply_text("Generic error occurred")
        raise e


def fallback_action(update: Update, context):
    update.message.reply_text(language.HOW_TO_USE_IT)


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
        states={
            CHOOSING: [
                MessageHandler(Filters.text, boardgame_selection_from_name),
                CallbackQueryHandler(suggest_from_boardgame)
            ]
        },
        fallbacks=[],
        per_message=False
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
    conversation()
