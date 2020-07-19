from bisect import bisect
from typing import List

from .utils import s


class PageSelection:
    '''A selection of pages (not necessarily continuous).'''
    def __init__(self, page_amount: int):
        self.page_amount: int = page_amount
        self.selection: List[slice] = [slice(0, page_amount)]

    def add(self, interval: slice):
        '''Add an interval of pages into the selection.'''
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

    def __str__(self):
        return ', '.join(
            f'{interval.start + 1}–{interval.stop}'
            if interval.start != interval.stop - 1
            else str(interval.start + 1)
            for interval in self.selection
        )


class PrintJob:
    '''An object representing a document to print with the printing options.'''
    def __init__(self, container, file):
        self.container = container
        self.file = file
        self.copies = 1
        self.pages = None
        self.toner_save = True

    def __str__(self):
        '''Return a neat job summary with all the options.'''
        return (
            f'{self.copies} cop{s(self.copies, "ies", "y")}, pages {str(self.pages)}\n'
            f'Toner-save is {"ON" if self.toner_save else "OFF"}'
        )
