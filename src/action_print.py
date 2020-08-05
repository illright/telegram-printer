from telegram import Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
)


def start_print_job(update: Update, context: CallbackContext):
    '''Start the printing job.'''
    id = update.callback_query.data.split(':')[0]
    job = context.bot_data['jobs'][id]

    job.start(on_finish=lambda: context.bot_data['jobs'].pop(id))

    update.effective_message.edit_text(
        'Sent to printing!'
    )
    update.callback_query.answer('Submitted for printing!')




print_handler = CallbackQueryHandler(start_print_job, pattern='[0-9a-f]+:print')
