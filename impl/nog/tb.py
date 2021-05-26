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
LOG_CTX_WIDTH = 50
VAR_COL_WIDTH = 15


class HiliteAdapter(logging.LoggerAdapter):
    def __init__(self):
        # self._lexer = pygments.lexers.get_lexer_by_name('pypylog')
        # self._lexer = pygments.lexers.get_lexer_by_name('py3tb')
        # self._lexer = pygments.lexers.get_lexer_by_name('python')
        self._lexer = pygments.lexers.PythonLexer()
        # self._formatter = pygments.formatters.terminal256.Terminal256Formatter()
        self._formatter = pygments.formatters.terminal256.TerminalTrueColorFormatter(
            style='monokai'
        )
        # self._formatter = pygments.formatters.get_formatter_by_name('terminal256')
        # self._formatter = pygments.formatters.html.HtmlFormatter()

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
        msg = self.highlight(msg)
        return msg, kwargs

    def highlight(self, s):
        return pygments.highlight(
            s,
            lexer=self._lexer,
            formatter=self._formatter,
        ).rstrip()


def traceback_with_local_vars(etype, value, tb):
    with HiliteAdapter() as log:
        log.error(f'{etype}: {value}')

        while True:
            if not tb.tb_next:
                break
            tb = tb.tb_next
        stack = []
        f = tb.tb_frame
        while f:
            stack.append(f)
            f = f.f_back

        stack.reverse()
        log_exception(log, etype, value, tb)

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
            fmtpp(log, frame.f_locals)

        log_exception(log, etype, value, tb)


def log_exception(log, etype, value, tb):
    log.error('')
    log.error('Exception:')
    for s in (
        s2
        for s1 in traceback.format_exception(etype, value, tb)
        for s2 in s1.splitlines()
    ):
        log.error(f'  {s.strip()}')


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
    return min(w, 150)


def fmtpp(log, kv, indent=2, width=None, sort_dicts=True, compact=True):
    width = width or get_width()
    s = pprint.pformat(kv, indent=indent, width=width, sort_dicts=sort_dicts, compact=compact)
    for line in s.splitlines():
        log.error(f'  {line}')
