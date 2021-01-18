from enum import Enum, auto

from telegram import Update, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
)

from ..number_up_layout import number_up_options
from ..print_job import PrintJob
from ..utils import s, get_inline_keyboard


class State(Enum):
    '''The states of the conversation.'''
    SELECT_SETTING = auto()
    SELECT_GRID = auto()


def status_text(job: PrintJob) -> str:
    '''Return the readable description of the current settings.'''
    text = '<b>Current settings</b>:\n'
    if job.pages.total != 1:
        if job.duplex:
            text += ' •  Printing on both sides of the page\n'
        else:
            text += ' •  Printing on only one side of the page\n'
    # if job.toner_save:
    #     text += ' •  Toner-save is enabled\n'
    # else:
    #     text += ' •  Toner-save is disabled\n'
    if job.pages.total != 1:
        text += f' •  {job.pages.per_page} document page{s(job.pages.per_page)} per 1 physical page'

    return text


def get_keyboard(job: PrintJob) -> InlineKeyboardMarkup:
    '''Return the keyboard with the conversation's actions.'''
    prefix = f'{job.id}:advanced:'
    layout = [
        None,
        None,
        # None,
        [('🔙 Back', prefix + 'back')],
    ]

    if job.pages.total != 1:
        if job.duplex:
            layout[0] = [('📄 Print on one side only', prefix + 'duplex')]
        else:
            layout[0] = [('📄 Print on both sides', prefix + 'duplex')]

        if job.pages.per_page < max(number_up_options):
            layout[1] = [('📖 Print more pages on one page', prefix + 'grid')]
        else:
            layout[1] = [('📖 Print less pages on one page', prefix + 'grid')]

    # if job.toner_save:
    #     layout[2] = [('⚫️ Disable toner-save mode', prefix + 'toner_save')]
    # else:
    #     layout[2] = [('⚪️ Enable toner-save mode', prefix + 'toner_save')]

    return get_inline_keyboard(layout)


def update_advanced(update: Update, context: CallbackContext) -> State:
    '''Let the user change advanced settings.'''
    id = update.callback_query.data.split(':')[0]
    job = context.bot_data['jobs'][id]
    context.user_data['current_job'] = job

    job.status_message.edit_text(
        status_text(job),
        parse_mode=ParseMode.HTML,
        reply_markup=get_keyboard(job),
    )
    update.callback_query.answer()

    return State.SELECT_SETTING


def toggle_duplex(update: Update, context: CallbackContext):
    '''Toggle the duplex setting.'''
    job = context.user_data['current_job']
    update.callback_query.answer()
    job.duplex = not job.duplex

    job.status_message.edit_text(
        status_text(job),
        parse_mode=ParseMode.HTML,
        reply_markup=get_keyboard(job),
    )


def toggle_toner_save(update: Update, context: CallbackContext):
    '''Toggle the toner save setting.'''
    job = context.user_data['current_job']
    update.callback_query.answer()
    job.toner_save = not job.toner_save

    job.status_message.edit_text(
        status_text(job),
        parse_mode=ParseMode.HTML,
        reply_markup=get_keyboard(job),
    )


def initiate_grid_selection(update: Update, context: CallbackContext) -> State:
    '''Present the options for the amount of document pages per physical page.'''
    job = context.user_data['current_job']
    update.callback_query.answer()

    prefix = f'{job.id}:advanced:grid'
    job.status_message.edit_text(
        f'For compactness, you can lay out up to {max(number_up_options)} pages of a document '
        'on a physical page.\n\n'
        'Select the desired amount of pages:',
        reply_markup=get_inline_keyboard([
            [(str(amt), f'{prefix}:{amt}')
             for amt in number_up_options
             if amt != job.pages.per_page],
            [('🔙 Back', f'{prefix}:back')]
        ]),
    )

    return State.SELECT_GRID


def set_grid(update: Update, context: CallbackContext) -> State:
    '''Modify the amount of document pages per physical page.'''
    job = context.user_data['current_job']
    grid_value = update.callback_query.data.split(':')[-1]
    if grid_value.isdigit():
        job.pages.per_page = int(grid_value)

    update.callback_query.answer()
    job.status_message.edit_text(
        status_text(job),
        parse_mode=ParseMode.HTML,
        reply_markup=get_keyboard(job),
    )

    return State.SELECT_SETTING


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


advanced_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(update_advanced, pattern='[0-9a-f]+:advanced')],
    states={
        State.SELECT_SETTING: [
            CallbackQueryHandler(toggle_duplex, pattern='[0-9a-f]+:advanced:duplex'),
            CallbackQueryHandler(toggle_toner_save, pattern='[0-9a-f]+:advanced:toner_save'),
            CallbackQueryHandler(initiate_grid_selection, pattern='[0-9a-f]+:advanced:grid'),
            CallbackQueryHandler(end_conversation, pattern='[0-9a-f]+:advanced:back'),
        ],
        State.SELECT_GRID: [
            CallbackQueryHandler(set_grid, pattern='[0-9a-f]+:advanced:grid:'),
        ]
    },
    fallbacks=[],
)
