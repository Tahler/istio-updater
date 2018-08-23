"""Functions which block until certain conditions."""

import collections
import datetime
import logging
import subprocess
import time
from typing import Callable

import sh

RETRY_INTERVAL = datetime.timedelta(seconds=5)


def until(predicate: Callable[[], bool],
          retry_interval_seconds: int = RETRY_INTERVAL.seconds) -> None:
    """Calls predicate every RETRY_INTERVAL until it returns True."""
    while not predicate():
        time.sleep(retry_interval_seconds)


def _until_rollouts_complete(resource_type: str, namespace: str) -> None:
    proc = sh.run_kubectl(
        [
            '--namespace', namespace, 'get', resource_type, '-o',
            'jsonpath={.items[*].metadata.name}'
        ],
        check=True)
    resources = collections.deque(proc.stdout.split(' '))
    logging.info('waiting for %ss in %s (%s) to rollout', resource_type,
                 namespace, ', '.join(resources))
    while len(resources) > 0:
        resource = resources.popleft()
        try:
            # kubectl blocks until ready.
            sh.run_kubectl(
                [
                    '--namespace', namespace, 'rollout', 'status',
                    resource_type, resource
                ],
                check=True)
        except subprocess.CalledProcessError as e:
            msg = 'failed to check rollout status of {}'.format(resource)
            if 'watch closed' in e.stderr:
                logging.debug('%s; retrying later', msg)
                resources.append(resource)
            else:
                logging.error(msg)


def until_deployments_are_ready(namespace: str) -> None:
    """Blocks until namespace's deployments' rollout statuses are complete."""
    _until_rollouts_complete('deployment', namespace)
