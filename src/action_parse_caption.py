from telegram import Update, ParseMode
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
)


def parse_caption(update: Update, context: CallbackContext):
    '''Use the ranges in the caption as the page selection.'''
    id = update.callback_query.data.split(':')[0]
    job = context.bot_data['jobs'][id]
    job.parse_caption()

    job.status_message.edit_text(
        job.get_message_text(),
        parse_mode=ParseMode.HTML,
        reply_markup=job.get_keyboard(),
    )
    update.callback_query.answer()


parse_caption_handler = CallbackQueryHandler(parse_caption, pattern='[0-9a-f]+:parse_caption')
