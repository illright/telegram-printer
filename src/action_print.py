from telegram import Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
)


def start_print_job(update: Update, context: CallbackContext):
    '''Start the printing job.'''
    id = update.callback_query.data.split(':')[0]
    job = context.user_data['files'][id]
    context.user_data['current_job'] = job
    context.user_data['effective_message'] = update.effective_message

    job.start()

    update.effective_message.edit_text(
        'Sent to printing!'
    )
    update.callback_query.answer()

    return ConversationHandler.END


# print_handler = ConversationHandler(
#     entry_points=[CallbackQueryHandler(start_print_job, pattern='[0-9a-f]+:print')],
#     states={},
#     fallbacks=[],
# )

print_handler = CallbackQueryHandler(start_print_job, pattern='[0-9a-f]+:print')
