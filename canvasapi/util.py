from __future__ import absolute_import, division, print_function, unicode_literals

import os
from collections import Iterable

from six import binary_type, string_types, text_type


def is_multivalued(value):
    """
    Determine whether the given value should be treated as a sequence
    of multiple values when used as a request parameter.

    In general anything that is iterable is multivalued.  For example,
    `list` and `tuple` instances are multivalued.  Generators are
    multivalued, as are the iterable objects returned by `zip`,
    `itertools.chain`, etc.  However, a simple `int` is single-valued.
    `str` and `bytes` are special cases: although these are iterable,
    we treat each as a single value rather than as a sequence of
    isolated characters or bytes.
    """

    # special cases: iterable, but not multivalued
    if isinstance(value, (string_types, binary_type)):
        return False

    # general rule: multivalued if iterable
    return isinstance(value, Iterable)


def combine_kwargs(**kwargs):
    """
    Flatten a series of keyword arguments from complex combinations of
    dictionaries and lists into a list of tuples representing
    properly-formatted parameters to pass to the Requester object.

    :param kwargs: A dictionary containing keyword arguments to be
        flattened into properly-formatted parameters.
    :type kwargs: dict

    :returns: A list of tuples that represent flattened kwargs. The
        first element is a string representing the key. The second
        element is the value.
    :rtype: `list` of `tuple`
    """
    combined_kwargs = []

    # Loop through all kwargs provided
    for kw, arg in kwargs.items():
        if isinstance(arg, dict):
            for k, v in arg.items():
                for tup in flatten_kwarg(k, v):
                    combined_kwargs.append(("{}{}".format(kw, tup[0]), tup[1]))
        elif is_multivalued(arg):
            for i in arg:
                for tup in flatten_kwarg("", i):
                    combined_kwargs.append(("{}{}".format(kw, tup[0]), tup[1]))
        else:
            combined_kwargs.append((text_type(kw), arg))

    return combined_kwargs


def flatten_kwarg(key, obj):
    """
    Recursive call to flatten sections of a kwarg to be combined

    :param key: The partial keyword to add to the full keyword
    :type key: str
    :param obj: The object to translate into a kwarg. If the type is
        `dict`, the key parameter will be added to the keyword between
        square brackets and recursively call this function. If the type
        is `list`, or `tuple`, a set of empty brackets will be appended
        to the keyword and recursively call this function. Otherwise,
        the function returns with the final keyword and value.

    :returns: A list of tuples that represent flattened kwargs. The
        first element is a string representing the key. The second
        element is the value.
    :rtype: `list` of `tuple`
    """
    if isinstance(obj, dict):
        # Add the word (e.g. "[key]")
        new_list = []
        for k, v in obj.items():
            for tup in flatten_kwarg(k, v):
                new_list.append(("[{}]{}".format(key, tup[0]), tup[1]))
        return new_list

    elif is_multivalued(obj):
        # Add empty brackets (i.e. "[]")
        new_list = []
        for i in obj:
            for tup in flatten_kwarg(key + "][", i):
                new_list.append((tup[0], tup[1]))
        return new_list
    else:
        # Base case. Return list with tuple containing the value
        return [("[{}]".format(text_type(key)), obj)]


def obj_or_id(parameter, param_name, object_types):
    """
    Accepts either an int (or long or str representation of an integer)
    or an object. If it is an int, return it. If it is an object and
    the object is of correct type, return the object's id. Otherwise,
    throw an exception.

    :param parameter: int, str, long, or object
    :param param_name: str
    :param object_types: tuple
    :rtype: int
    """
    from canvasapi.user import User

    try:
        return int(parameter)
    except (ValueError, TypeError):
        # Special case where 'self' is a valid ID of a User object
        if User in object_types and parameter == "self":
            return parameter

        for obj_type in object_types:
            if isinstance(parameter, obj_type):
                try:
                    return int(parameter.id)
                except Exception:
                    break

        obj_type_list = ",".join([obj_type.__name__ for obj_type in object_types])
        message = "Parameter {} must be of type {} or int.".format(
            param_name, obj_type_list
        )
        raise TypeError(message)


def get_institution_url(base_url):
    """
    Clean up a given base URL.

    :param base_url: The base URL of the API.
    :type base_url: str
    :rtype: str
    """
    base_url = base_url.rstrip("/")
    index = base_url.find("/api/v1")

    if index != -1:
        return base_url[0:index]

    return base_url


def file_or_path(file):
    """
    Open a file and return the handler if a path is given.
    If a file handler is given, return it directly.

    :param file: A file handler or path to a file.

    :returns: A tuple with the open file handler and whether it was a path.
    :rtype: (file, bool)
    """

    is_path = False
    if isinstance(file, string_types):
        if not os.path.exists(file):
            raise IOError("File at path " + file + " does not exist.")
        file = open(file, "rb")
        is_path = True

    return file, is_path


def normalize_bool(val, param_name):
    """
    Normalize boolean-like strings to their corresponding boolean values.

    :param val: Value to normalize. Acceptable values:
        True, "True", "true", False, "False", "false"
    :type val: str or bool
    :param param_name: Name of the parameter being checked
    :type param_name: str

    :rtype: bool
    """
    if isinstance(val, bool):
        return val
    elif val in ("True", "true"):
        return True
    elif val in ("False", "false"):
        return False
    else:
        raise ValueError(
            'Parameter `{}` must be True, "True", "true", False, "False", or "false".'.format(
                param_name
            )
        )


def clean_headers(headers):
    """
    Sanitize a dictionary containing HTTP headers of sensitive values.

    :param headers: The headers to sanitize.
    :type headers: dict
    :returns: A list of headers without sensitive information stripped out.
    :rtype: dict
    """
    cleaned_headers = headers.copy()

    authorization_header = headers.get("Authorization")
    if authorization_header:
        # Grab the actual token (not the "Bearer" prefix)
        _, token = authorization_header.split(" ")

        # Trim all but the last four characters
        sanitized = "****" + token[-4:]

        cleaned_headers["Authorization"] = sanitized

    return cleaned_headers
