# -*- coding: utf-8 -*-
"""Utilities to deal with various mapping data structures."""
from aiida.common import AttributeDict


def get_logging_container():
    """Return an `AttributeDict` that can be used to map logging messages to certain log levels.

    This datastructure is useful to add log messages in a function that does not have access to the right logger. Once
    returned, the caller who does have access to the logger can then easily loop over the contents and pipe the messages
    through the actual logger.

    :return: :py:class:`~aiida.common.extendeddicts.AttributeDict`
    """
    return AttributeDict({
        'debug': [],
        'info': [],
        'warning': [],
        'error': [],
        'critical': [],
    })