#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

# I got this from http://svn.navi.cx/misc/trunk/djblets/djblets/util/decorators.py     (sbf)
# It should make useful template tag creation much less tedious and annoying when
# needing any complex functionality such as access to the context or a block
# This is part of the djiblets template library.

#
# decorators.py -- Miscellaneous, useful decorators.  This might end up moving
#                  to something with a different name.
#
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
#
#

import inspect

import django.template


# The decorator decorator.  This is copyright unknown, verbatim from
# http://wiki.python.org/moin/PythonDecoratorLibrary
def simple_decorator(decorator):
    """Thi decorator can be used to turn simple functions into well-behaved
    decorators, so long as the decorators are fairly simple.

    If a decorator expects a function and returns a function (no
    descriptors), and if it doesn't modify function attributes or
    docstring, then it is eligible to use this. Simply apply
    @simple_decorator to your decorator and it will automatically
    preserve the docstring and function attributes of functions to which
    it is applied.
    """

    def new_decorator(f):
        g = decorator(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g

    # Now a few lines needed to make simple_decorator itself
    # be a well-behaved decorator.
    new_decorator.__name__ = decorator.__name__
    new_decorator.__doc__ = decorator.__doc__
    new_decorator.__dict__.update(decorator.__dict__)
    return new_decorator


def basictag(takes_context=False):
    """A decorator similar to Django's @register.simple_tag that optionally
    takes a context parameter. This condenses many tag implementations down to
    a few lines of code.

    Example:
        @register.tag
        @basictag(takes_context=True)
        def printuser(context):
            return context['user']
    """

    class BasicTagNode(django.template.Node):
        def __init__(self, takes_context, tag_name, tag_func, args):
            self.takes_context = takes_context
            self.tag_name = tag_name
            self.tag_func = tag_func
            self.args = args

        def render(self, context):
            args = [django.template.Variable(var).resolve(context) for var in self.args]

            if self.takes_context:
                return self.tag_func(context, *args)
            else:
                return self.tag_func(*args)

    def basictag_func(tag_func):
        def _setup_tag(_parser, token):
            bits = token.split_contents()
            tag_name = bits[0]
            del bits[0]

            # noinspection PyDeprecation
            params, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = inspect.getfullargspec(tag_func)
            max_args = len(params)

            if takes_context:
                if params[0] == 'context':
                    max_args -= 1  # Ignore context
                else:
                    raise django.template.TemplateSyntaxError(
                        "Any tag function decorated with takes_context=True "
                        "must have a first argument of 'context'"
                    )

            min_args = max_args - len(defaults or [])

            if not min_args <= len(bits) <= max_args:
                if min_args == max_args:
                    raise django.template.TemplateSyntaxError(
                        f"{tag_name!r} tag takes {min_args:d} arguments."
                    )
                else:
                    raise django.template.TemplateSyntaxError(
                        "{!r} tag takes {:d} to {:d} arguments, got {:d}.".format(
                            tag_name,
                            min_args,
                            max_args,
                            len(bits),
                        )
                    )

            return BasicTagNode(takes_context, tag_name, tag_func, bits)

        _setup_tag.__name__ = tag_func.__name__
        _setup_tag.__doc__ = tag_func.__doc__
        _setup_tag.__dict__.update(tag_func.__dict__)
        return _setup_tag

    return basictag_func


def blocktag(tag_func):
    """A decorator similar to Django's @register.simple_tag that does all the
    redundant work of parsing arguments and creating a node class in order to
    render content between a foo and endfoo tag block. This condenses many tag
    implementations down to a few lines of code.

    Example:
        @register.tag
        @blocktag
        def divify(context, nodelist, div_id=None):
            s = "<div"
            if div_id:
                s += " id='%s'" % div_id
            return s + ">" + nodelist.render(context) + "</div>"
    """

    class BlockTagNode(django.template.Node):
        def __init__(self, tag_name, tag_func, nodelist, args):
            self.tag_name = tag_name
            self.tag_func = tag_func
            self.nodelist = nodelist
            self.args = args

        def render(self, context):
            args = [django.template.Variable(var).resolve(context) for var in self.args]
            return self.tag_func(context, self.nodelist, *args)

    def _setup_tag(parser, token):
        bits = token.split_contents()
        tag_name = bits[0]
        del bits[0]

        # noinspection PyDeprecation
        params, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = inspect.getfullargspec(tag_func)
        max_args = len(params) - 2  # Ignore context and nodelist
        min_args = max_args - len(defaults or [])

        if not min_args <= len(bits) <= max_args:
            if min_args == max_args:
                raise django.template.TemplateSyntaxError(
                    "{!r} tag takes {:d} arguments.".format(
                        tag_name,
                        min_args,
                    )
                )
            else:
                raise django.template.TemplateSyntaxError(
                    "{!r} tag takes {:d} to {:d} arguments, got {:d}.".format(
                        tag_name,
                        min_args,
                        max_args,
                        len(bits),
                    )
                )

        nodelist = parser.parse(
            ('end%s' % tag_name),
        )
        parser.delete_first_token()
        return BlockTagNode(tag_name, tag_func, nodelist, bits)

    _setup_tag.__name__ = tag_func.__name__
    _setup_tag.__doc__ = tag_func.__doc__
    _setup_tag.__dict__.update(tag_func.__dict__)
    return _setup_tag
