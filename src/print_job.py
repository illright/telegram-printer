import os
from typing import List, BinaryIO
from uuid import uuid4

import PyPDF4
from telegram import InlineKeyboardMarkup, File

from .utils import s, get_inline_keyboard


from .page_selection import PageSelection


class PrintJob:
    '''An object representing a document to print with the printing options.'''
    def __init__(self, container: BinaryIO, file: File, converted: bool, toner_save: bool = True):
        reader = PyPDF4.PdfFileReader(container)
        page_amount = reader.getNumPages()
        landscape_pages = 0
        portrait_pages = 0
        for page in reader.pages:
            rotation = page.get('/Rotate')
            width = page.mediaBox.getUpperRight_x() - page.mediaBox.getUpperLeft_x()
            height = page.mediaBox.getUpperRight_y() - page.mediaBox.getLowerRight_y()
            if (width > height) == (rotation in (0, 180, None)):
                landscape_pages += 1
            else:
                portrait_pages += 1

        self.container = container
        self.file = file
        self.converted = converted
        self.copies = 1
        self.pages = PageSelection(reader.numPages)
        self.toner_save = toner_save
        self.portrait = portrait_pages > landscape_pages
        self.duplex = self.pages.total != 1
        self.id = uuid4().hex

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

    def get_command(self) -> List[str]:
        '''Generate the command for `lp` to execute this print job.'''
        if self.duplex:
            duplex = f'sides=two-sided-{"long" if self.portrait else "short"}-edge'
        else:
            duplex = 'sides=one-sided'

        return [
            'lp',
            '-d', os.getenv('PRINTER'),
            '-t', self.id,
            '-n', str(self.copies),
            '-P', repr(self.pages),
            '-o', f'number-up={self.pages_per_page}',
            '-o', duplex,
            '-o', f'print-quality={3 if self.toner_save else 5}'
            '-'
        ]
