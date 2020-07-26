from bisect import bisect
from typing import List, BinaryIO
from uuid import uuid4

import PyPDF4
from telegram import InlineKeyboardMarkup, File

from .utils import s, get_inline_keyboard


class PageSelection:
    '''A selection of pages (not necessarily continuous).'''

    def __init__(self, page_amount: int):
        self.page_amount: int = page_amount
        self.selection: List[slice] = [slice(0, page_amount)]

    def validate(self, interval: slice) -> slice:
        '''Ensure the interval is valid and within page bounds.'''
        left = max(interval.start, 0)
        right = min(interval.stop, self.page_amount)
        return slice(left, max(left, right))

    def add(self, interval: slice):
        '''Add an interval of pages into the selection.'''
        interval = self.validate(interval)

        if interval.start == interval.stop:
            return

        if not self.selection:
            self.selection.append(interval)
            return

        idx = bisect(self.selection, interval)
        left = self.selection[idx - 1] if idx != 0 else None

        if left is not None and interval.start <= left.stop:
            self.selection[idx - 1] = slice(left.start, max(interval.stop, left.stop))
        else:
            self.selection.insert(idx, interval)
            idx += 1

        while idx < len(self.selection):
            right = self.selection[idx]

            if right.stop <= interval.stop:
                self.selection.pop(idx)
            elif right.start <= interval.stop:
                self.selection[idx - 1] = slice(self.selection[idx - 1].start, right.stop)
                self.selection.pop(idx)
                break
            else:
                break

    def remove(self, interval: slice):
        '''Remove an interval of pages into the selection.'''
        interval = self.validate(interval)

        if interval.start == interval.stop:
            return

        if not self.selection:
            return

        idx = bisect(self.selection, interval)
        left = self.selection[idx - 1] if idx != 0 else None

        if left is not None and interval.start < left.stop:
            if interval.start < left.start:
                self.selection.pop(idx - 1)
            else:
                if left.start == interval.start:
                    self.selection.pop(idx - 1)
                    idx -= 1
                else:
                    self.selection[idx - 1] = slice(left.start, interval.start)
                if interval.stop < left.stop:
                    self.selection.insert(idx, slice(interval.stop, left.stop))

        while idx < len(self.selection):
            right = self.selection[idx]

            if interval.stop <= right.start:
                break

            if right.stop <= interval.stop:
                self.selection.pop(idx)
            else:
                self.selection[idx] = slice(interval.stop, right.stop)
                if interval.start < right.start:
                    self.selection.insert(idx, slice(right.start, interval.start))

    def __str__(self) -> str:
        string = ', '.join(
            f'{interval.start + 1}–{interval.stop}'
            if interval.start != interval.stop - 1
            else str(interval.start + 1)
            for interval in self.selection
        ) or 'None'

        if self.selection[0] == slice(0, self.page_amount):
            string += ' (all)'

        return string

    def __bool__(self) -> bool:
        return bool(self.selection)


class PrintJob:
    '''An object representing a document to print with the printing options.'''
    def __init__(self, container: BinaryIO, file: File, converted: bool, toner_save: bool = True):
        reader = PyPDF4.PdfFileReader(container)
        page_amount = reader.getNumPages()

        self.container = container
        self.file = file
        self.converted = converted
        self.copies = 1
        self.pages = PageSelection(page_amount)
        self.toner_save = toner_save
        self.duplex = page_amount != 1
        self.pages_per_page = 1
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
        if self.pages.page_amount != 1:
            text += f' •  Pages: {str(self.pages)}\n'
            text += f' •  Printing on {"both sides" if self.duplex else "one side"} of the page\n'
        if self.pages_per_page != 1:
            text += f' •  {self.pages_per_page} page{s(self.pages_per_page)} per page\n'
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

        if self.pages.page_amount == 1:
            layout[2].pop(0)

        return get_inline_keyboard(layout)
