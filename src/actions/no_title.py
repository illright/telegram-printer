from telegram import Update, ParseMode
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
)


def exclude_title(update: Update, context: CallbackContext):
    '''Exclude the title page.'''
    id = update.callback_query.data.split(':')[0]
    job = context.bot_data['jobs'][id]
    job.pages.remove(slice(0, 1))

    job.status_message.edit_text(
        job.get_message_text(),
        parse_mode=ParseMode.HTML,
        reply_markup=job.get_keyboard(),
    )
    update.callback_query.answer()


no_title_handler = CallbackQueryHandler(exclude_title, pattern='[0-9a-f]+:no_title')
