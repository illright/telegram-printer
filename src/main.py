import os
from secrets import compare_digest
from tempfile import NamedTemporaryFile

from dotenv import load_dotenv
from telegram import Update, ParseMode
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    MessageHandler,
    Updater,
)
from telegram.ext.filters import Filters

from .option_pages import pages_handler
from .option_copies import copies_handler
from .print_job import PrintJob
from .utils import convert_to_pdf


load_dotenv()
AUTH_TOKEN = os.getenv('AUTH_TOKEN')

MAX_DOWNLOAD_SIZE_MB = 20
MAX_DOWNLOAD_SIZE = MAX_DOWNLOAD_SIZE_MB * 1024 * 1024


def authenticate(update: Update, context: CallbackContext):
    '''Check the authentication token on first interaction with the bot.'''
    their_auth_token = context.args[0] if context.args else ''

    if (not context.user_data.get('authenticated', False)
            and not compare_digest(their_auth_token, AUTH_TOKEN)):
        update.message.reply_text(
            'I only serve the <s>Soviet Union</s> Innopolis University.\n'
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
    if not context.user_data.get('authenticated', False) and False:
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

    converted = convert_to_pdf(container, update.message.document.mime_type)

    job = PrintJob(container, file, converted, toner_save=context.user_data.get('toner_save', True))

    context.user_data.setdefault('files', {})
    context.user_data['files'][job.id] = job

    update.message.reply_text(
        str(job),
        reply_to_message_id=update.message.message_id,
        reply_markup=job.get_keyboard(),
    )


updater = Updater(os.getenv('BOT_API_TOKEN'), use_context=True)

updater.dispatcher.add_handler(CommandHandler('start', authenticate))
updater.dispatcher.add_handler(MessageHandler(Filters.document, process_file))
updater.dispatcher.add_handler(pages_handler)
updater.dispatcher.add_handler(copies_handler)
