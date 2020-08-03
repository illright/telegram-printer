from typing import BinaryIO
from uuid import uuid4

from PyPDF4 import PdfFileReader
from telegram import InlineKeyboardMarkup

from .cups_server import cups, printer
from .number_up_layout import layouts
from .page_selection import PageSelection
from .utils import s, get_inline_keyboard, is_portrait


class PrintJob:
    '''An object representing a document to print with the printing options.'''
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

        self.container.seek(0)

    def __str__(self) -> str:
        '''Return a neat job summary with all the options.'''
        if not self.pages:
            return 'No pages selected, I can\'t print nothing'

        text = (
            f'<b>Ready to print!</b>\n'
            f' •  {self.copies} cop{s(self.copies, "ies", "y")}\n'
        )
        if self.pages.total != 1:
            text += f' •  Pages: {str(self.pages)}\n'
            text += f' •  Printing on {"both sides" if self.duplex else "one side"} of the page\n'
        if self.pages.per_page != 1:
            text += f' •  {self.pages.per_page} page{s(self.pages.per_page)} per page\n'
        if self.toner_save:
            text += ' •  Toner-save is <u>enabled</u>'

        return text

    def get_keyboard(self) -> InlineKeyboardMarkup:
        '''Return an inline keyboard allowing to change the current settings.'''
        prefix = f'{self.id}:'

        layout = [
            self.pages and [('Print', prefix + 'print')],
            self.converted and [('Preview', prefix + 'preview')],
            [('Pages', prefix + 'pages'), ('Copies', prefix + 'copies')],
            [('Advanced settings', prefix + 'advanced')]
        ]

        if self.pages.total == 1:
            layout[2].pop(0)

        return get_inline_keyboard(layout)

    def start(self):
        '''Initiate a print job with all the settings.'''
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
