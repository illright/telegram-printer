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

    update.callback_query.answer('Submitted for printing!')


def cancel_print_job(update: Update, context: CallbackContext):
    '''Cancel the printing job.'''
    id = update.callback_query.data.split(':')[0]
    context.bot_data['jobs'].pop(id).cancel()

    update.callback_query.answer('Printing cancelled!')


print_handler = CallbackQueryHandler(start_print_job, pattern='[0-9a-f]+:print')
cancel_handler = CallbackQueryHandler(cancel_print_job, pattern='[0-9a-f]+:cancel')
