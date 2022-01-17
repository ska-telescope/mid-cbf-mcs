# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada
"""Module for Mid.CBF MCS utils."""

from __future__ import annotations  # allow forward references in type hints

import functools
import threading
from types import FunctionType
from typing import Any, Callable

CHECK_THREAD_SAFETY = False


class ThreadsafeCheckingMeta(type):  # pragma: no cover
    """Metaclass that checks for methods being run by multiple concurrent threads."""

    @staticmethod
    def _init_wrap(func: Callable) -> Callable:
        """
        Wrap ``__init__`` to add thread safety checking stuff.

        :param func: the ``__init__`` method being wrapped

        :return: a wrapped ``__init__`` method
        """

        @functools.wraps(func)
        def _wrapper(self: ThreadsafeCheckingMeta, *args: Any, **kwargs: Any) -> None:
            self._thread_id = {}  # type: ignore[attr-defined]
            func(self, *args, **kwargs)

        return _wrapper

    @staticmethod
    def _check_wrap(func: Callable) -> Callable:
        """
        Wrap the class methods that injects thread safety checks.

        :param func: the method being wrapped

        :return: the wrapped method
        """

        @functools.wraps(func)
        def _wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            thread_id = threading.current_thread().ident

            try:
                if func in self._thread_id:
                    assert (
                        self._thread_id[func] != thread_id
                    ), f"Method {func} has been re-entered by thread {thread_id}"

                    is_threadsafe = getattr(func, "_is_threadsafe", False)
                    assert (
                        is_threadsafe
                    ), f"Method {func} is already being run by thread {self._thread_id[func]}."
            except AssertionError:
                raise
            except Exception as exception:
                raise ValueError(
                    f"Exception when trying to run method {func}"
                ) from exception

            self._thread_id[func] = thread_id
            try:
                return func(self, *args, **kwargs)
            finally:
                # thread-safey way to delete this key, without caring if it has already
                # been deleted by another thread (because we might be multithreading
                # through this wrapper if the wrapped method is marked threadsafe).
                self._thread_id.pop(func, None)

        return _wrapper

    def __new__(
        cls: type[ThreadsafeCheckingMeta], name: str, bases: tuple[type], attrs: dict
    ) -> ThreadsafeCheckingMeta:
        """
        Construct Class.

        :param name: name of the new class
        :param bases: parent classes of the new class
        :param attrs: class attributes

        :return: new class
        """
        if CHECK_THREAD_SAFETY:
            methods = [attr for attr in attrs if isinstance(attrs[attr], FunctionType)]
            for attr_name in methods:
                if attr_name == "__init__":
                    attrs[attr_name] = cls._init_wrap(attrs[attr_name])
                elif attr_name in ["__getattr__", "__setattr__"]:
                    pass
                else:
                    attrs[attr_name] = cls._check_wrap(attrs[attr_name])

        return super(ThreadsafeCheckingMeta, cls).__new__(cls, name, bases, attrs)


def threadsafe(func: Callable) -> Callable:  # pragma: no cover
    """
    Use this method as a decorator for marking a method as threadsafe.

    This tells the ``ThreadsafeCheckingMeta`` metaclass that it is okay
    for the decorated method to have more than one thread in it at a
    time. The metaclass will still raise an exception if the *same*
    thread enters the method multiple times, because re-entry is a
    common cause of deadlock.

    :param func: the method to be marked as threadsafe

    :return: the method, marked as threadsafe
    """
    func._is_threadsafe = True  # type: ignore[attr-defined]
    return func