from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

from testcontainers.lifecycle.startable import Startable

_EXECUTOR_PREFIX = "testcontainers-lifecycle"
_EXECUTOR = ThreadPoolExecutor(thread_name_prefix=_EXECUTOR_PREFIX)


def deep_start(*startables: Startable) -> Future[None]:
    return _deep_start({}, list(startables))


def _deep_start(started: dict[Startable, Future[None]], startables: list[Startable]) -> Future[None]:
    futures: list[Future[None]] = []

    for startable in startables:
        started_copy = dict(started)

        if startable in started:
            future = started[startable]
        else:
            dependencies = list(startable.dependencies)
            dependencies_future = _deep_start(started_copy, dependencies)
            future = _then_run_async(dependencies_future, startable.start)
            started[startable] = future
            started.update(started_copy)

        futures.append(future)

    return _all_of_failfast(futures)


def _then_run_async(dependency: Future[None], fn: Callable[[], None]) -> Future[None]:
    result: Future[None] = Future()

    def complete_from(future: Future[None]) -> None:
        try:
            future.result()
            result.set_result(None)
        except BaseException as exc:
            result.set_exception(exc)

    def dependency_done(future: Future[None]) -> None:
        try:
            future.result()
        except BaseException as exc:
            result.set_exception(exc)
            return

        _EXECUTOR.submit(fn).add_done_callback(complete_from)

    dependency.add_done_callback(dependency_done)
    return result


def _all_of_failfast(futures: list[Future[None]]) -> Future[None]:
    result = Future()

    if not futures:
        result.set_result(None)
        return result

    remaining = len(futures)

    def done(f: Future[None]):
        nonlocal remaining

        if result.done():
            return

        try:
            f.result()
        except BaseException as exc:
            result.set_exception(exc)
            return

        remaining -= 1
        if remaining == 0:
            result.set_result(None)

    for future in futures:
        future.add_done_callback(done)

    return result
