from telegram import Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
)


def send_preview(update: Update, context: CallbackContext):
    '''Cancel the printing job.'''
    id = update.callback_query.data.split(':')[0]
    job = context.bot_data['jobs'][id]

    update.effective_message.reply_document(
        job.container,
        filename=job.container.original_name[:job.container.original_name.rfind('.')] + '.pdf',
        caption='For best results, save the file as PDF manually.',
        reply_to_message_id=update.effective_message.reply_to_message.message_id,
    )
    job.container.seek(0)
    update.callback_query.answer()


preview_handler = CallbackQueryHandler(send_preview, pattern='[0-9a-f]+:preview')
