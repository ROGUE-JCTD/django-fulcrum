from __future__ import absolute_import

from hashlib import md5
from django.core.cache import cache
from multiprocessing import Process
import time
import django
from django.core.exceptions import AppRegistryNotReady, ImproperlyConfigured
from django.db import OperationalError
import json


class FulcrumTaskRunner:

    def __init__(self):
        name = "FulcrumTasks"
        file_name_hexdigest = md5(name).hexdigest()
        self.lock_id = '{0}-lock-{1}'.format(name, file_name_hexdigest)

    def start(self, interval=30):
        """Calls Run() sets an interval time
        Args:
            interval: An integer in seconds for the polling interval.
        """

        if self.add_lock():
                process = Process(target=self.run, args=(interval,))
                process.daemon = True
                process.start()

    def run(self, interval):
        """Checks the 'lock' from the cache if using multiprocessing module, update if it exists.
        Args:
            interval: An integer in seconds for the polling interval.
        """
        while self.is_locked():
            try:
                from .tasks import task_update_layers, pull_s3_data
            except AppRegistryNotReady:
                django.setup()
                from .tasks import task_update_layers, pull_s3_data
            try:
                try:
                    from django.contrib.auth.models import User
                except ImproperlyConfigured:
                    pass
                if User.objects.filter(id=1):
                    print("Updating Layers...")
                    task_update_layers()
                    print("Pulling S3 Data...")
                    pull_s3_data()
            except OperationalError as e:
                print("Database isn't ready yet.")
                print(e.message)
                print(e.args)
            time.sleep(interval)

    def stop(self):
        """Removes the 'lock' from the cache if using multiprocessing module."""
        cache.delete(self.lock_id)

    def add_lock(self):
        """Adds a lock to a queue so multiple processes don't break the lock."""
        if cache.add(self.lock_id, json.dumps(['lock']), timeout=None):
            return True
        else:
            old_value = json.loads(cache.get(self.lock_id))
            cache.set(self.lock_id, json.dumps(old_value + ['lock']))
            return False

    def is_locked(self):
        """Checks the lock."""
        if cache.get(self.lock_id):
            return True
        return False

    def remove_lock(self):
        """Removes a lock to a queue so multiple processes don't break the lock."""
        lock = json.loads(cache.get(self.lock_id))
        if len(lock) <= 1:
            cache.delete(self.lock_id)
        else:
            cache.set(self.lock_id, json.dumps(lock[:-1]))

    def __del__(self):
        """Used to remove the placeholder on the cache if using the multiprocessing module."""
        self.remove_lock()
