import re
from datetime import datetime
from typing import BinaryIO
from uuid import uuid4

from PyPDF4 import PdfFileReader
from telegram import InlineKeyboardMarkup, ParseMode

from .cups_server import cups, printer
from .number_up_layout import layouts
from .page_selection import PageSelection
from .utils import s, get_inline_keyboard, is_portrait, apply_page_selection

page_range_ptn = re.compile(r'([0-9]+)(?:\s*[-–]\s*([0-9]+))?')


class PrintJob:
    '''An object representing a document to print with the printing options.'''
    STATE_PREPARING = 1
    STATE_SENT = 2
    STATE_EXPIRED = 3
    STATE_DONE = 4

    def __init__(self, container: BinaryIO, converted: bool, caption: str, toner_save: bool = True):
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
        self.created_at = datetime.now()
        self.potential_page_ranges = page_range_ptn.findall(caption)

        self.container.seek(0)

    def get_message_text(self) -> str:
        '''Return the message text that is appropriate for the current state and settings.'''
        if not self.pages:
            return 'No pages selected, I can\'t print nothing'

        if self.state == self.STATE_PREPARING:
            text = '<b>Ready to print!</b>\n'
        elif self.state == self.STATE_SENT:
            text = '<b>Sent for printing!</b>\n'
        elif self.state == self.STATE_EXPIRED:
            text = '<b>Job expired</b>\nForward the file to print again.\n'
        elif self.state == self.STATE_DONE:
            text = '<b>Job completed</b>\nForward the file to print again.\n'
        else:
            text = '<b>Something broke down :(</b>'

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
                None,
                None,
                [('Pages', prefix + 'pages'), ('Copies', prefix + 'copies')],
                [('Advanced settings', prefix + 'advanced')],
            ]

            if self.pages.total == 1:
                # Remove the `Pages` button
                layout[4].pop(0)

            if not self.portrait and self.pages.total > 5 and 1 in self.pages:
                layout[2] = [('💡 Exclude the title page', prefix + 'no_title')]

            if self.potential_page_ranges:
                layout[3] = [('💡 Select the pages in the caption', prefix + 'parse_caption')]
        else:
            layout = None

        return get_inline_keyboard(layout)

    def parse_caption(self):
        '''Initialize the page selection with the ranges from the caption.'''
        self.pages.clear()

        for range in self.potential_page_ranges:
            if not range[1]:
                self.pages.add(slice(int(range[0]) - 1, int(range[0])))
            else:
                self.pages.add(slice(int(range[0]) - 1, int(range[1])))

        self.potential_page_ranges = None

    def start(self):
        '''Initiate a print job with all the settings.'''
        layout = layouts[self.pages.per_page]
        print_options = {
            'multiple-document-handling': 'separate-documents-collated-copies',
            'copies': str(self.copies),
            'print-quality': '3' if self.toner_save else '5',
            'number-up': str(self.pages.per_page),
            'number-up-layout': 'btlr',
            'media': 'a4',
        }

        if self.pages.per_page == 1:
            print_options['page-ranges'] = repr(self.pages)
        else:
            # The printer setting for page ranges applies after the N-up,
            #   which is counter-intuitive, so we exclude pages manually
            apply_page_selection(self.container, self.pages)

        if self.duplex:
            length = 'long' if self.portrait == layout.is_portrait else 'short'
            print_options['sides'] = f'two-sided-{length}-edge'
        else:
            print_options['sides'] = 'one-sided'

        self.job_index = cups.printFile(printer, self.container.name, self.id, print_options)
        self.state = self.STATE_SENT
        self.status_message.edit_text(
            self.get_message_text(),
            parse_mode=ParseMode.HTML,
        )

    def expire(self):
        '''Expire the job, freeing up its resources.'''
        self.container.close()
        if self.state == self.STATE_SENT:
            self.state = self.STATE_DONE
        else:
            self.state = self.STATE_EXPIRED

        self.status_message.edit_text(
            self.get_message_text(),
            parse_mode=ParseMode.HTML,
        )
