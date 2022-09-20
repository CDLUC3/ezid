#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD
'''
Implements logging filters configured under settings.py like:

'filters': {
   'reduce_unreadable_post_errors' : {
        '()' : 'impl.log_filters.ReduceUnreadablePostErrors'
    },
    ...
'handlers': {
    'mail_admins': {
        'level': 'ERROR',
        'filters': ['require_debug_false','reduce_unreadable_post_errors'],
        'class': 'common.utils.log.AdminEmailHandlerWithEmail'
     },


See also: https://stackoverflow.com/questions/15544124/django-unreadableposterror-request-data-read-error
'''

import logging
import random
import django.http


class ReduceUnreadablePostErrors(logging.Filter):
    '''
    Filters out most of those UnreadablePostError exceptions.

    Some are let through since they may be indicative of a problem at times, but these
    appear to be mostly, if not all, client side errors over which we have no control.
    '''
    def filter(self, record):
        if record.exc_info:
            exc_value = record.exc_info[1]
            if isinstance(exc_value, django.http.UnreadablePostError):
                return random.randint(1,20) % 20==0
        return True
