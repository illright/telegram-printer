import re
from enum import Enum, auto

from telegram import Update, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
)
from telegram.ext.filters import Filters

from ..cups_server import cups, printer
from ..print_job import PrintJob
from ..utils import s, get_inline_keyboard


class State(Enum):
    '''The states of the conversation.'''
    UPDATE = auto()


max_copies = cups.getPrinterAttributes(
    printer,
    requested_attributes=['copies-supported']
).get('copies-supported', (1, 9999))[1]
number_ptn = re.compile('[0-9]+')
copies_fmt = (
    'Currently printing {job.copies} cop{s}.\n\n'
    'How many copies should be printed (e.g. 10)?'
)


def get_keyboard(job: PrintJob) -> InlineKeyboardMarkup:
    '''Return the keyboard with the conversation's actions.'''
    prefix = f'{job.id}:copies:'
    layout = [
        [('➖', prefix + 'dec'), ('➕', prefix + 'inc')],
        [('🔙 Back', prefix + 'back')],
    ]

    return get_inline_keyboard(layout)


def update_copies(update: Update, context: CallbackContext) -> State:
    '''Let the user change how many copies are being printed.'''
    id = update.callback_query.data.split(':')[0]
    job = context.bot_data['jobs'][id]
    context.user_data['current_job'] = job

    job.status_message.edit_text(
        copies_fmt.format(job=job, s=s(job.copies, 'ies', 'y')),
        reply_markup=get_keyboard(job),
    )
    update.callback_query.answer()

    return State.UPDATE


def process_input(update: Update, context: CallbackContext):
    '''Change the amount of copies arbitrarily.'''
    job = context.user_data['current_job']
    old_copies = job.copies
    job.copies = min(max(1, int(context.matches[0].group())), max_copies)

    if job.copies != old_copies:
        job.status_message.edit_text(
            copies_fmt.format(job=job, s=s(job.copies, 'ies', 'y')),
            reply_markup=get_keyboard(job),
        )

    update.message.delete()


def increment(update: Update, context: CallbackContext):
    '''Add one more copy.'''
    job = context.user_data['current_job']
    job.copies += 1

    job.status_message.edit_text(
        copies_fmt.format(job=job, s=s(job.copies, 'ies', 'y')),
        reply_markup=get_keyboard(job),
    )
    update.callback_query.answer()


def decrement(update: Update, context: CallbackContext):
    '''Subtract one copy.'''
    job = context.user_data['current_job']
    if job.copies > 1:
        job.copies -= 1

        job.status_message.edit_text(
            copies_fmt.format(job=job, s=s(job.copies, 'ies', 'y')),
            reply_markup=get_keyboard(job),
        )
        update.callback_query.answer()
    else:
        update.callback_query.answer('Cannot have less than one copy')


def end_conversation(update: Update, context: CallbackContext) -> int:
    '''End the conversation and show the job status again.'''
    job = context.user_data['current_job']
    update.callback_query.answer()

    job.status_message.edit_text(
        job.get_message_text(),
        parse_mode=ParseMode.HTML,
        reply_markup=job.get_keyboard(),
    )

    context.user_data.pop('current_job')

    return ConversationHandler.END


def unrecognized(update: Update, _context: CallbackContext):
    '''Guide the user if they are unsure of what to write.'''
    update.message.reply_text(
        'I don\'t see numbers here 👀\n\n'
        'You can specify the amount of copies with a single number.\n'
        'Examples:\n'
        ' •  <code>1</code>\n'
        ' •  <code>10</code>\n',
        parse_mode=ParseMode.HTML,
    )


copies_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(update_copies, pattern='[0-9a-f]+:copies')],
    states={
        State.UPDATE: [
            MessageHandler(Filters.regex(number_ptn), process_input),
            CallbackQueryHandler(increment, pattern='[0-9a-f]+:copies:inc'),
            CallbackQueryHandler(decrement, pattern='[0-9a-f]+:copies:dec'),
            CallbackQueryHandler(end_conversation, pattern='[0-9a-f]+:copies:back'),
        ],
    },
    fallbacks=[MessageHandler(Filters.text, unrecognized)],
)
