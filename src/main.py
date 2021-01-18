import os
from datetime import datetime, timedelta
from secrets import compare_digest
from tempfile import NamedTemporaryFile

from cups_notify.event import CupsEvent
from telegram import Update, ParseMode
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    Updater,
)
from telegram.ext.filters import Filters

from .action_no_title import no_title_handler
from .action_parse_caption import parse_caption_handler
from .action_print import print_handler, cancel_handler
from .action_preview import preview_handler
from .cups_server import notifier
from .option_pages import pages_handler
from .option_copies import copies_handler
from .option_advanced import advanced_handler
from .print_job import PrintJob
from .utils import convert_to_pdf


AUTH_TOKEN = os.getenv('AUTH_TOKEN')

MAX_DOWNLOAD_SIZE_MB = 20
MAX_DOWNLOAD_SIZE = MAX_DOWNLOAD_SIZE_MB * 1024 * 1024


def authenticate(update: Update, context: CallbackContext):
    '''Check the authentication token on first interaction with the bot.'''
    their_auth_token = context.args[0] if context.args else ''

    if (not context.user_data.get('authenticated', False)
            and not compare_digest(their_auth_token, AUTH_TOKEN)):
        update.message.reply_text(
            'I only serve <s>the Soviet Union</s> Innopolis University.\n'
            'Prove your worth by scanning the QR code above the printer. Then we\'ll talk.',
            parse_mode=ParseMode.HTML,
        )
    else:
        context.user_data['authenticated'] = True
        update.message.reply_text(
            'Greetings! Send me any files you want to print and, with any luck, '
            'they\'ll soon be awaiting you at the student printer (5th floor).'
        )
        update.message.reply_text(
            'You\'ll notice that toner save is on by default. '
            'This just means that the printed text is lighter than regular, '
            'but still very readable. You can turn it off for some documents specifically '
            'or turn off by default with the /toner_save command.\n'
            'Consider using it for non-critical printing~'
        )


def process_file(update: Update, context: CallbackContext):
    '''Accept a file from a user and set up a print job.'''
    if not context.user_data.get('authenticated', False):
        update.message.reply_text(
            'I will not fulfill your request until you prove your worth.\n'
            'Scan the QR code above the student printer on the 5th floor'
        )
        return

    if update.message.document.file_size > MAX_DOWNLOAD_SIZE:
        update.message.reply_text(f'Sorry, I only work with files up to {MAX_DOWNLOAD_SIZE_MB} MB')
        return

    file = update.message.document.get_file()
    container = NamedTemporaryFile()
    file.download(out=container)
    container.original_name = update.message.document.file_name

    converted = convert_to_pdf(container, update.message.document.mime_type)

    job = PrintJob(container,
                   converted,
                   update.message.caption,
                   toner_save=context.user_data.get('toner_save', True))
    context.bot_data.setdefault('jobs', {})[job.id] = job

    job.status_message = update.message.reply_text(
        job.get_message_text(),
        parse_mode=ParseMode.HTML,
        reply_to_message_id=update.message.message_id,
        reply_markup=job.get_keyboard(),
    )


def toggle_toner_save(update: Update, context: CallbackContext):
    '''Toggle the default setting for toner save mode.'''
    context.user_data['toner_save'] = not context.user_data.get('toner_save', True)
    if context.user_data['toner_save']:
        update.message.reply_text(
            'Toner save enabled by default! To turn it off, use the /toner_save command again.\n'
        )
    else:
        update.message.reply_text(
            'Toner save disabled by default! To turn it on, use the /toner_save command again.\n'
        )


def catch_cups_event(event: CupsEvent):
    '''A listener callback to CUPS events.'''
    print(event)


def clean_up(context: CallbackContext):
    '''Expire the jobs that were created more than an hour ago.'''
    time_limit = datetime.now() - timedelta(hours=1)
    jobs = context.bot_data.get('jobs', {})
    expired_ids = []
    for job_id in jobs.keys():
        if jobs[job_id].created_at < time_limit:
            jobs[job_id].expire()
            expired_ids.append(job_id)
    for job_id in expired_ids:
        jobs.pop(job_id)


persistence = PicklePersistence(filename='data.pkl', store_bot_data=False)
updater = Updater(os.getenv('BOT_API_TOKEN'), persistence=persistence, use_context=True)
updater.job_queue.run_repeating(clean_up, timedelta(hours=1))

updater.dispatcher.add_handler(CommandHandler('start', authenticate))
updater.dispatcher.add_handler(CommandHandler('toner_save', toggle_toner_save))
updater.dispatcher.add_handler(MessageHandler(Filters.document, process_file))
updater.dispatcher.add_handler(pages_handler)
updater.dispatcher.add_handler(copies_handler)
updater.dispatcher.add_handler(advanced_handler)
updater.dispatcher.add_handler(print_handler)
updater.dispatcher.add_handler(cancel_handler)
updater.dispatcher.add_handler(preview_handler)
updater.dispatcher.add_handler(no_title_handler)
updater.dispatcher.add_handler(parse_caption_handler)

notifier.subscribe(catch_cups_event)
