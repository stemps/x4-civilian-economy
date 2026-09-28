"""Optional wall-clock stage and unittest timings, independent of MD execution."""
from collections import defaultdict
from contextlib import contextmanager
import sys
from time import perf_counter
import unittest


class Timings:
    def __init__(self, enabled=False, stream=None):
        self.enabled = enabled
        self.stream = stream if stream is not None else sys.stderr
        self.stages = []
        self.tests = []

    @contextmanager
    def stage(self, name):
        start = perf_counter()
        try:
            yield
        finally:
            if self.enabled:
                self.stages.append((name, perf_counter() - start))

    def runner(self):
        if not self.enabled:
            return unittest.TextTestRunner(verbosity=2)
        timings = self

        class TimedResult(unittest.TextTestResult):
            def startTest(self, test):
                super().startTest(test)
                self.started = perf_counter()

            def stopTest(self, test):
                timings.tests.append((test.id(), perf_counter() - self.started))
                super().stopTest(test)

        return unittest.TextTestRunner(verbosity=2, resultclass=TimedResult)

    def report(self):
        if not self.enabled:
            return
        print('\nWall-clock timings (seconds; test times include setup/cleanup):', file=self.stream)
        for name, elapsed in self.stages:
            print(f'  {name}: {elapsed:.3f}', file=self.stream)
        modules = defaultdict(float)
        counts = defaultdict(int)
        for name, elapsed in self.tests:
            module = name.split('.')[0]
            modules[module] += elapsed
            counts[module] += 1
        if self.tests:
            print('  Modules:', file=self.stream)
            for name, elapsed in sorted(modules.items(), key=lambda item: -item[1]):
                print(f'    {name}: {elapsed:.3f} ({counts[name]} tests)', file=self.stream)
            print('  Slowest tests:', file=self.stream)
            for name, elapsed in sorted(self.tests, key=lambda item: -item[1])[:10]:
                print(f'    {elapsed:.3f} {name}', file=self.stream)
