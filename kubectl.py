"""Abstractions for common calls to kubectl."""

import contextlib
import socket
import subprocess
import tempfile
from typing import Any, Dict, Generator, List

import yaml

import sh


def apply_file(path: str) -> None:
    sh.run_kubectl(['apply', '-f', path], check=True)


def apply_text(json_or_yaml: str, intermediate_file_path: str = None) -> None:
    """Creates/updates resources described in either JSON or YAML string.

    Uses `kubectl apply -f FILE`.

    Args:
        json_or_yaml: contains either the JSON or YAML manifest of the
                resource(s) to apply; applied through an intermediate file
        intermediate_file_path: if set, defines the file to write to (useful
                for debugging); otherwise, uses a temporary file
    """
    if intermediate_file_path is None:
        opener = tempfile.NamedTemporaryFile(mode='w+')
    else:
        opener = open(intermediate_file_path, 'w+')

    with opener as f:
        f.write(json_or_yaml)
        f.flush()
        apply_file(f.name)
