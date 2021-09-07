"""Traceback formatter for console output

This traceback formatter is based on the following thoughts:

- In the console, the command line prompt is the focus point for user interaction, and the lines
that immediately precede the prompt are prime real estate, visible without any scrolling, and likely
to be the first place where the eyes focus after having just written the command that caused the
output.

- The further away from the command line prompt the output is, the longer it takes to get to it,
since the text is usually reached by scrolling up from the prompt. So it's also less likely that the
output will be seen at all.

- So we want to print traceback and related troubleshooting output in increasing order of
importance. Least import first and most important last.

- Providing traceback and related output in increasing order of importance minimizes the average
amount of scrolling that will need to be done in order to pick up the information required in order
to address the issue.

- Increasing the amount of output also increases the amount of scrolling required for finding the
information that is important for the particular issue.

- In general, the most valuable traceback is the one that contains the stack frame in which the
initial exception occurred. Stack frames are less valuable the further away they are from the stack
frame in which the exception occurred.

- Chained exceptions (exceptions that occurred while processing the initial exception) have their
own tracebacks. The stack frames in those tracebacks contain the call frames for the calls starting
at the exception handler for the previous exception, and ending at the frame in which the next
exception occurred. That may be valuable, but it's less valuable than the initial exception.

- Dumps of local variables may be valuable, but they come at a cost of having to scroll past them
when they are not being referenced.

- The traceback contains static "post mortem" information, useful for quickly fixing bugs, but at
some point, it becomes counterproductive to add more information to the traceback, as analyzing it
will take longer than reproducing the issue and stepping through it in a debugger.

- Based on the above, this formats the traceback as follows, in order of most to last valuable
information (with most valuable printed last):

- Brief exception information that contains the source location where the initial exception was
raised, and text and type of the raised exception object.

- Brief exception info for the [3] stack frames leading up to the initial exception.

- Brief information about chained exceptions, pulled only from the raising frame in each traceback.

- Repeat of the brief information, but this time including dump of variables available in each
frame.
"""

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import logging
import pathlib
import pprint
import shutil
import traceback

import pygments
import pygments.formatters
import pygments.formatters.html
import pygments.formatters.terminal256
import pygments.lexers
import pygments.styles
import textwrap

# print(list(pygments.lexers.get_all_lexers()))
# print(list(pygments.formatters.get_all_formatters()))
# print(list(pygments.styles.get_all_styles()))

#    ERROR impl.nog.tb tb 11167 140120135037056
# Number of characters per line to use if it cannot be detected (normally due to stdout is not a
# terminal).
DEFAULT_TERMINAL_WIDTH = 150
# Number of characters in the section of text printed at the start of log lines (determined by the
# log format). This is subtracted from the total width to determine the space available for
# formatted output.
LOG_CTX_WIDTH = 10

VAR_COL_WIDTH = 15


def traceback_with_local_vars(etype, value, tb):
    with HiliteAdapter() as log:
        tb_iter = tb
        while True:
            if not tb_iter.tb_next:
                break
            tb_iter = tb_iter.tb_next
        stack = []
        f = tb_iter.tb_frame
        while f:
            stack.append(f)
            f = f.f_back

        stack.reverse()

        # log_exception(log, etype, value, tb, 150)

        for frame in stack:
            log.error('')
            p = pathlib.Path(frame.f_code.co_filename)
            s = 'File "{}", line {}, in {}'.format(
                p.as_posix(),
                frame.f_lineno,
                frame.f_code.co_name,
            )
            wrap(log, s)
            log.error('')
            fmtpp(log, frame.f_locals, highlight=False)

        # log.error('')
        # log.error('~' * 100)
        # log.error('Exception, only primary, minimal, source code locations, most recent FIRST')

        # log_exception(log, etype, value, tb, 150)

        sep(log)

        log_exception(log, etype, value, tb)

        sep(log)

        wrap(log, f'{etype}:')
        wrap(log, f'  {value}')
        # sep(log)


def log_exception(log, etype, value, tb, width=150, chain=False):
    log.error('')
    # log.error('')
    # log.error('Exception:')
    for s in (
            s2
            for s1 in traceback.format_exception(etype, value, tb, chain=False)
            for s2 in s1.splitlines()
    ):
        # log.error(f'  {s.strip()}')
        # log.error(f'  {s}')
        log.error(s)


def wrap(log, s, initial_indent=0, subsequent_indent=2):
    for s in textwrap.wrap(
            s,
            width=get_width(),
            initial_indent=' ' * initial_indent,
            subsequent_indent=' ' * subsequent_indent,
    ):
        log.error(s)


def get_width():
    w = shutil.get_terminal_size().columns - LOG_CTX_WIDTH - 1
    return min(w, DEFAULT_TERMINAL_WIDTH)


def fmtpp(log, kv, indent=2, width=None, sort_dicts=True, compact=True, highlight=True):
    width = width or get_width()
    s = pprint.pformat(
        kv, indent=indent, width=width, sort_dicts=sort_dicts, compact=compact
    )
    if highlight:
        s = highlighter.highlight(s)
    for line in s.splitlines():
        log.error(f'  {line}')


def sep(log):
    log.error('~' * get_width())


# def highlight(self, s):
#     return pygments.highlight(
#         s,
#         lexer=self._lexer,
#         formatter=self._formatter,
#     ).rstrip()


class Highlighter:
    def __init__(self):
        self._lexer = pygments.lexers.PythonLexer()
        self._formatter = pygments.formatters.terminal256.TerminalTrueColorFormatter(
            style='monokai'
        )

    def highlight(self, s):
        return pygments.highlight(
            s,
            lexer=self._lexer,
            formatter=self._formatter,
        ).rstrip()


class HiliteAdapter(logging.LoggerAdapter):
    def __init__(self, width=150):
        self._highlighter = Highlighter()
        logger = self.make_logger()
        super().__init__(logger, {})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def make_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        return logger

    def process(self, msg, kwargs):
        msg = self._highlighter.highlight(msg)
        return msg, kwargs


highlighter = Highlighter()
