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
        return ', '.join(
            f'{interval.start + 1}–{interval.stop}'
            if interval.start != interval.stop - 1
            else str(interval.start + 1)
            for interval in self.selection
        ) or 'None'

    def __bool__(self) -> bool:
        return bool(self.selection)


class PrintJob:
    '''An object representing a document to print with the printing options.'''
    def __init__(self, container: BinaryIO, file: File, converted: bool, toner_save: bool = True):
        reader = PyPDF4.PdfFileReader(container)
        self.container = container
        self.file = file
        self.converted = converted
        self.copies = 1
        self.pages = PageSelection(reader.getNumPages())
        self.toner_save = toner_save
        self.id = uuid4().hex

        self.container.seek(0)

    def __str__(self) -> str:
        '''Return a neat job summary with all the options.'''
        if not self.pages:
            return 'No pages selected, I can\'t print nothing'

        return (
            f'Ready to print!\n\n'
            f'{self.copies} cop{s(self.copies, "ies", "y")}, pages: {str(self.pages)}\n'
            f'Toner-save is {"ON" if self.toner_save else "OFF"}'
        )

    def namespace(self, query: str) -> str:
        '''Namespace the callback query with own ID.'''
        return f'{self.id}:{query}'

    def get_keyboard(self) -> InlineKeyboardMarkup:
        '''Return an inline keyboard allowing to change the current settings.'''
        return get_inline_keyboard([
            self.pages and [('Print', self.namespace('print'))],
            self.converted and [('Preview', self.namespace('preview'))],
            [('Pages', self.namespace('pages')), ('Copies', self.namespace('copies'))],
        ])
