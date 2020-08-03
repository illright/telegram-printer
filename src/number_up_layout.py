from collections import namedtuple

from .cups_server import cups, printer

Layout = namedtuple('Layout', ['x_pages', 'y_pages', 'is_portrait'])

layouts = {
    1: Layout(1, 1, is_portrait=True),
    2: Layout(1, 2, is_portrait=False),
    4: Layout(2, 2, is_portrait=True),
    6: Layout(2, 3, is_portrait=False),
    9: Layout(3, 3, is_portrait=True),
}

number_up_options = sorted(
    set(layouts.keys()).intersection(
        cups.getPrinterAttributes(
            printer,
            requested_attributes=['number-up-supported']
        ).get('number-up-supported', (1,))
    )
)
