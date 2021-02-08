import logging
import sys
import traceback

log = logging.getLogger(__name__)


def traceback_with_local_vars():
    tb = sys.exc_info()[2]
    while 1:
        if not tb.tb_next:
            break
        tb = tb.tb_next
    stack = []
    f = tb.tb_frame
    while f:
        stack.append(f)
        f = f.f_back

    stack.reverse()

    for line in traceback.format_exc().splitlines(keepends=False):
        log.error(line)

    for frame in stack:
        log.error(
            '{}:{}'.format(
                frame.f_code.co_name,
                frame.f_code.co_filename,
                frame.f_lineno,
            )
        )
        for k, v in list(frame.f_locals.items()):
            try:
                v = str(v)
            except Exception as e:
                v = '<{}>'.format(str(e))
            log.error('  {:20s} = {}'.format(k, v))
