import re

from telegram.ext import CallbackContext


print_job_title_ptn = re.compile(r'Print Job: [\w-]+ \(([0-9a-f]+)\) (\w+)')
printed_pages_ptn = re.compile(r'Printed (\d+) page\(s\)\.')


def process_cups_event(context: CallbackContext):
    '''Handling function for CUPS events to update jobs' statuses.'''
    event = context.job.context
    print(event)
    title_match = print_job_title_ptn.fullmatch(event.title)
    if title_match is None:
        return

    job_id, operation = title_match.group(1, 2)
    try:
        context.bot_data['jobs'][job_id].process_event(event, operation)
    except KeyError:
        pass
