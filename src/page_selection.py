from bisect import bisect
from math import ceil
from typing import List, Generator


class PageSelection:
    '''A selection of pages (not necessarily continuous).'''

    def __init__(self, page_amount: int):
        self.total: int = page_amount
        self.selection: List[slice] = [slice(0, page_amount)]
        self.per_page = 1

    def validate(self, interval: slice) -> slice:
        '''Ensure the interval is valid and within page bounds.'''
        left = max(interval.start, 0)
        right = min(interval.stop, self.total)
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

        if self.selection and self.selection[0] == slice(0, self.total):
            string += ' (all)'

        return string

    def __repr__(self) -> str:
        return ','.join(
            f'{interval.start + 1}-{interval.stop}'
            if interval.start != interval.stop - 1
            else str(interval.start + 1)
            for interval in self.selection
        )

    def __bool__(self) -> bool:
        return bool(self.selection)

    def __iter__(self) -> Generator[int, None, None]:
        for interval in self.selection:
            for idx in range(interval.start, interval.stop):
                yield idx

    def __contains__(self, page):
        idx = bisect(self.selection, slice(page, page + 1))
        if idx - 1 in range(len(self.selection)):
            interval = self.selection[idx - 1]
            return page in range(interval.start, interval.stop + 1)
        return False

    @property
    def n_up(self) -> Generator[List[int], None, None]:
        '''Return a generator that yields lists of pages for the N-up grouping.'''
        iterator = iter(self)
        pages_left = True

        while pages_left:
            composed_page = []
            try:
                for _ in range(self.per_page):
                    composed_page.append(next(iterator))
            except StopIteration:
                pages_left = False
            if composed_page:
                yield composed_page

    @property
    def to_print(self) -> int:
        '''Return the actual amount of pages that this selection will print.'''
        pages = sum(
            len(range(interval.start, interval.stop))
            for interval in self.selection
        )
        return ceil(pages / self.per_page)
