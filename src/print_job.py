import re
from math import ceil
from typing import BinaryIO, Callable
from uuid import uuid4

from cups_notify.event import CupsEvent
from PyPDF4 import PdfFileReader
from telegram import InlineKeyboardMarkup, ParseMode

from .cups_server import cups, printer
from .number_up_layout import layouts
from .page_selection import PageSelection
from .utils import s, get_inline_keyboard, is_portrait


printed_pages_ptn = re.compile(r'Printed (\d+) page\(s\)\.')


class PrintJob:
    '''An object representing a document to print with the printing options.'''
    STATE_PREPARING = 1
    STATE_SENT = 2
    STATE_IN_PROGRESS = 3
    STATE_DONE = 4
    STATE_CANCELED = 5
    STATE_ERROR = 6

    def __init__(self, container: BinaryIO, converted: bool, toner_save: bool = True):
        reader = PdfFileReader(container)

        self.container = container
        self.converted = converted
        self.copies = 1
        self.pages = PageSelection(reader.numPages)
        self.toner_save = toner_save
        self.duplex = self.pages.total != 1
        self.portrait = is_portrait(reader)
        self.id = uuid4().hex
        self.job_index = None
        self.status_message = None
        self.state = self.STATE_PREPARING
        self.progress = None
        self.on_finish = None

        self.container.seek(0)

    def get_message_text(self) -> str:
        '''Return the message text that is appropriate for the current state and settings.'''
        if not self.pages:
            return 'No pages selected, I can\'t print nothing'

        if self.state == self.STATE_PREPARING:
            text = '<b>Ready to print!</b>\n'
        elif self.state == self.STATE_SENT:
            text = '<b>Sent for printing!</b>\n'
        elif self.state == self.STATE_IN_PROGRESS:
            text = (
                '<b>Printing in progress</b>\n'
                + self.draw_progressbar() + '\n'
            )
        elif self.state == self.STATE_DONE:
            text = '<b>All done!</b>\n'
        elif self.state == self.STATE_CANCELED:
            text = '<b>Job canceled</b>\n'
        else:
            text = '<b>Something broke down :(</b>\n'

        text += f' •  {self.copies} cop{s(self.copies, "ies", "y")}\n'
        if self.pages.total != 1:
            text += f' •  Pages: {str(self.pages)}\n'
            text += f' •  Printing on {"both sides" if self.duplex else "one side"} of the page\n'
        if self.pages.per_page != 1:
            text += f' •  {self.pages.per_page} page{s(self.pages.per_page)} per page\n'
        if self.toner_save:
            text += ' •  Toner-save is <u>enabled</u>'

        if self.converted and self.state == self.STATE_PREPARING:
            text += (
                '\n\n<i>Note:</i> this file was converted to PDF for printing. '
                'Some formatting details may have been lost, '
                'preview the conversion result to be sure.'
            )

        return text

    def get_keyboard(self) -> InlineKeyboardMarkup:
        '''Return an inline keyboard that is appropriate for the current state and settings.'''
        prefix = f'{self.id}:'

        if self.state == self.STATE_PREPARING:
            layout = [
                self.pages and [('Print', prefix + 'print')],
                self.converted and [('Preview', prefix + 'preview')],
                [('Pages', prefix + 'pages'), ('Copies', prefix + 'copies')],
                [('Advanced settings', prefix + 'advanced')]
            ]

            if self.pages.total == 1:
                # Remove the `Pages` button
                layout[2].pop(0)
        elif self.state == self.STATE_SENT:
            layout = [[('Cancel', prefix + 'cancel')]]
        else:
            layout = None

        return get_inline_keyboard(layout)

    def start(self, on_finish: Callable[[], None] = None):
        '''Initiate a print job with all the settings.'''
        self.on_finish = on_finish
        layout = layouts[self.pages.per_page]
        print_options = {
            'multiple-document-handling': 'separate-documents-collated-copies',
            'copies': str(self.copies),
            'print-quality': '3' if self.toner_save else '5',
            'number-up': str(self.pages.per_page),
            'number-up-layout': 'btlr',
        }

        if self.pages.per_page == 1:
            print_options['page-ranges'] = repr(self.pages)

        if self.duplex:
            length = 'long' if self.portrait == layout.is_portrait else 'short'
            print_options['sides'] = f'two-sided-{length}-edge'
        else:
            print_options['sides'] = 'one-sided'

        self.job_index = cups.printFile(printer, self.container.name, self.id, print_options)
        self.status_message.edit_text(
            self.get_message_text(),
            parse_mode=ParseMode.HTML,
        )

    def cancel(self):
        '''Cancel this print job.'''
        cups.cancelJob(self.job_index, purge_job=True)
        self.state = self.STATE_CANCELED
        self.status_message.edit_text(
            self.get_message_text(),
            parse_mode=ParseMode.HTML,
        )

    def process_event(self, event: CupsEvent, operation: str):
        '''React to a CUPS event, updating the state and the message text accordingly.'''
        if operation == 'held':
            self.state = self.STATE_SENT
        elif operation == 'completed':
            self.state = self.STATE_DONE
            self.on_finish()
        elif operation == 'processing':
            if event.description == f'Job #{self.job_index} started.':
                self.state = self.STATE_IN_PROGRESS
                self.progress = 0
            else:
                pages = printed_pages_ptn.fullmatch(event.description)
                divisor = 2 if self.duplex else 1
                if pages is None or int(pages.group(1)) != (self.progress + 1) // divisor:
                    self.state = self.STATE_ERROR
                else:
                    self.progress += 1
        else:
            self.state = self.STATE_ERROR

        self.status_message.edit_text(
            self.get_message_text(),
            parse_mode=ParseMode.HTML,
            reply_markup=self.get_keyboard(),
        )

    def draw_progressbar(self) -> str:
        '''Return a string with a progressbar of 10 cells.'''
        cells = ceil(self.progress / self.pages.to_print * 10)
        return ('▰' * cells).ljust(10, '▱') + f'  {self.progress}/{self.pages.to_print}'
