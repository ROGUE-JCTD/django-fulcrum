from __future__ import absolute_import

from hashlib import md5
from django.core.cache import caches
from multiprocessing import Process
import time
import django
from django.core.exceptions import AppRegistryNotReady, ImproperlyConfigured
from django.db import OperationalError
import json
import logging

logger = logging.getLogger(__file__)

class FulcrumTaskRunner:

    def __init__(self):
        name = "FulcrumTasks"
        file_name_hexdigest = md5(name).hexdigest()
        self.lock_id = '{0}-lock-{1}'.format(name, file_name_hexdigest)
        self.cache = caches['fulcrum']

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
                    User = get_user_model()
                    if User.objects.filter(id=-1).exists() or User.objects.filter(id=1).exists():
                        logging.info("Updating Layers...")
                        task_update_layers()
                        logging.info("Pulling S3 Data...")
                        pull_s3_data()
                except ImproperlyConfigured:
                    pass
            except OperationalError as e:
                logging.warn("Database isn't ready yet.")
                logging.warn(e.message)
                logging.warn(e.args)
            time.sleep(interval)

    def stop(self):
        """Removes the 'lock' from the cache if using multiprocessing module."""
        self.cache.delete(self.lock_id)

    def add_lock(self):
        """Adds a lock to a queue so multiple processes don't break the lock."""
        if self.cache.add(self.lock_id, json.dumps(['lock']), timeout=None):
            return True
        else:
            old_value = json.loads(self.cache.get(self.lock_id))
            self.cache.set(self.lock_id, json.dumps(old_value + ['lock']))
            return False

    def is_locked(self):
        """Checks the lock."""
        if self.cache.get(self.lock_id):
            return True
        return False

    def remove_lock(self):
        """Removes a lock to a queue so multiple processes don't break the lock."""
        lock = json.loads(self.cache.get(self.lock_id))
        if len(lock) <= 1:
            self.cache.delete(self.lock_id)
        else:
            self.cache.set(self.lock_id, json.dumps(lock[:-1]))

    def __del__(self):
        """Used to remove the placeholder on the cache if using the multiprocessing module."""
        self.remove_lock()
