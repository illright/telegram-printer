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

from .utils import s, get_inline_keyboard


class State(Enum):
    '''The states of the conversation.'''
    ADD = auto()
    REMOVE = auto()

page_range_ptn = re.compile(r'([0-9]+)(?:\s*[-–]\s*([0-9]+))?')
page_status_fmt = (
    'Currently selected pages: {job.pages}\n'
    'The document has {job.pages.total} page{s}.\n\n'
    'What pages should be {verbed} (e.g. 1 or 4-5)?'
)


def get_keyboard(state: State, id: str) -> InlineKeyboardMarkup:
    '''Return the keyboard that's appropriate for the current conversation state.'''
    prefix = f'{id}:pages:'
    layout = [
        None,
        None,
        [('🔙 Back', prefix + 'back')],
    ]
    if state == State.ADD:
        layout[0] = [('➖ I want to remove pages', prefix + 'remove')]
        layout[1] = [('📖 Add all pages', prefix + 'add_all')]
    else:
        layout[0] = [('➕ I want to add pages', prefix + 'add')]
        layout[1] = [('📖 Remove all pages', prefix + 'remove_all')]

    return get_inline_keyboard(layout)


def update_pages(update: Update, context: CallbackContext) -> State:
    '''Let the user change which pages are being printed.'''
    id = update.callback_query.data.split(':')[0]
    job = context.bot_data['jobs'][id]
    context.user_data['current_job'] = job

    job.status_message.edit_text(
        page_status_fmt.format(job=job, s=s(job.pages.total), verbed='added'),
        reply_markup=get_keyboard(State.REMOVE, id),
    )
    update.callback_query.answer()

    return State.REMOVE


def process_addition(update: Update, context: CallbackContext):
    '''Add a range of pages.'''
    job = context.user_data['current_job']
    old_selection = str(job.pages)
    for range in page_range_ptn.findall(update.message.text):
        if not range[1]:
            job.pages.add(slice(int(range[0]) - 1, int(range[0])))
        else:
            job.pages.add(slice(int(range[0]) - 1, int(range[1])))

    if str(job.pages) != old_selection:
        job.status_message.edit_text(
            page_status_fmt.format(job=job, s=s(job.pages.total), verbed='added'),
            reply_markup=get_keyboard(State.ADD, job.id),
        )

    update.message.delete()


def process_removal(update: Update, context: CallbackContext):
    '''Remove a range of pages.'''
    job = context.user_data['current_job']
    old_selection = str(job.pages)
    for range in page_range_ptn.findall(update.message.text):
        if not range[1]:
            job.pages.remove(slice(int(range[0]) - 1, int(range[0])))
        else:
            job.pages.remove(slice(int(range[0]) - 1, int(range[1])))

    if str(job.pages) != old_selection:
        job.status_message.edit_text(
            page_status_fmt.format(job=job, s=s(job.pages.total), verbed='removed'),
            reply_markup=get_keyboard(State.REMOVE, job.id),
        )

    update.message.delete()


def add_all(update: Update, context: CallbackContext) -> State:
    '''Add all pages.'''
    job = context.user_data['current_job']
    old_selection = str(job.pages)
    job.pages.add(slice(0, job.pages.total))

    if str(job.pages) != old_selection:
        job.status_message.edit_text(
            page_status_fmt.format(job=job, s=s(job.pages.total), verbed='removed'),
            reply_markup=get_keyboard(State.REMOVE, job.id),
        )

    update.callback_query.answer('Added all pages')
    return State.REMOVE


def remove_all(update: Update, context: CallbackContext) -> State:
    '''Remove all pages.'''
    job = context.user_data['current_job']
    old_selection = str(job.pages)
    job.pages.remove(slice(0, job.pages.total))

    if str(job.pages) != old_selection:
        job.status_message.edit_text(
            page_status_fmt.format(job=job, s=s(job.pages.total), verbed='added'),
            reply_markup=get_keyboard(State.ADD, job.id),
        )

    update.callback_query.answer('Removed all pages')
    return State.ADD


def switch_to_remove(update: Update, context: CallbackContext) -> State:
    '''Change the conversation state to remove pages instead.'''
    job = context.user_data['current_job']

    job.status_message.edit_text(
        page_status_fmt.format(job=job, s=s(job.pages.total), verbed='removed'),
        reply_markup=get_keyboard(State.REMOVE, job.id),
    )

    update.callback_query.answer()
    return State.REMOVE


def switch_to_add(update: Update, context: CallbackContext) -> State:
    '''Change the conversation state to add pages instead.'''
    job = context.user_data['current_job']

    job.status_message.edit_text(
        page_status_fmt.format(job=job, s=s(job.pages.total), verbed='added'),
        reply_markup=get_keyboard(State.ADD, job.id),
    )

    update.callback_query.answer()
    return State.ADD


def end_conversation(update: Update, context: CallbackContext) -> int:
    '''End the conversation and show the job status again.'''
    job = context.user_data['current_job']
    update.callback_query.answer()

    job.status_message.edit_text(
        str(job),
        parse_mode=ParseMode.HTML,
        reply_markup=job.get_keyboard(),
    )

    context.user_data.pop('current_job')

    return ConversationHandler.END


def unrecognized(update: Update, _context: CallbackContext):
    '''Guide the user if they are unsure of what to write.'''
    update.message.reply_text(
        'I don\'t see pages here 👀\n\n'
        'You can either write individual pages or ranges.\n'
        'Examples:\n'
        ' •  <code>1</code>\n'
        ' •  <code>2-24</code>\n'
        ' •  <code>1, 3-6, 8</code>',
        parse_mode=ParseMode.HTML,
    )


pages_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(update_pages, pattern='[0-9a-f]+:pages$')],
    states={
        State.ADD: [
            MessageHandler(Filters.regex(page_range_ptn), process_addition),
            CallbackQueryHandler(switch_to_remove, pattern='[0-9a-f]+:pages:remove$'),
            CallbackQueryHandler(add_all, pattern='[0-9a-f]+:pages:add_all'),
            CallbackQueryHandler(end_conversation, pattern='[0-9a-f]+:pages:back'),
        ],
        State.REMOVE: [
            MessageHandler(Filters.regex(page_range_ptn), process_removal),
            CallbackQueryHandler(switch_to_add, pattern='[0-9a-f]+:pages:add$'),
            CallbackQueryHandler(remove_all, pattern='[0-9a-f]+:pages:remove_all'),
            CallbackQueryHandler(end_conversation, pattern='[0-9a-f]+:pages:back'),
        ],
    },
    fallbacks=[MessageHandler(Filters.text, unrecognized)],
)
