#!/usr/bin/env python3

import argparse
from datetime import datetime
import logging
import os
import re
import tarfile
from typing import List, Tuple

import requests

import kubectl
import sh
import wait

_TAG_PATTERN = re.compile('export TAG="(.*)"')

DEFAULT_BRANCH = 'release-1.0'
DEFAULT_ARCH = 'linux'
DEFAULT_HELM_ARGS = [
    '--set=grafana.enabled=true',
    '--set=global.proxy.resources.requests.cpu=500m',
    '--set=global.defaultResources.requests.cpu=7000m',
    # '--set=pilot.replicaCount=4',
]


def _extract_tag(green_build: str) -> str:
    for line in green_build.split('\n'):
        matches = _TAG_PATTERN.match(line)
        if matches is not None:
            tag = matches.group(1)
            return tag
    raise ValueError()


def _get_green_build(branch: str) -> str:
    url = ('https://raw.githubusercontent.com/istio-releases/daily-release/'
           '{}/greenBuild.VERSION').format(branch)
    response = requests.get(url)
    return response.text


def _get_latest_istio_tag(branch: str) -> str:
    green_build = _get_green_build(branch)
    return _extract_tag(green_build)


def _download_file(url: str, out_path: str) -> None:
    logging.info('downloading %s to %s', url, out_path)
    sh.run(['curl', '--output', out_path, url], check=True)


def _download_istio_release(tag: str, arch: str, out_path: str) -> None:
    file_name = 'istio-{}-{}.tar.gz'.format(tag, arch)
    url = ('https://storage.googleapis.com/istio-prerelease/daily-build/'
           '{}/{}').format(tag, file_name)
    _download_file(url, out_path)


def _extract_archive(path: str, extracted_dir_path: str) -> str:
    """Extracts the .tar.gz at path to extracted_dir_path.

    Args:
        path: path to a .tar.gz archive file, containing a single directory
                when extracted
        extracted_dir_path: the destination in which to extract the contents
                of the archive

    Returns:
        the path to the single directory the archive contains
    """
    logging.info('extracting %s to %s', path, extracted_dir_path)
    with tarfile.open(path) as tar:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(tar, path=extracted_dir_path)
    extracted_items = os.listdir(extracted_dir_path)
    if len(extracted_items) != 1:
        raise ValueError(
            'archive at {} did not contain a single directory'.format(path))
    return os.path.join(extracted_dir_path, extracted_items[0])


def _apply_template(chart_path: str, namespace: str, helm_args: List[str],
                    intermediate_file_path: str) -> None:
    logging.info('applying chart at %s in namespace %s', chart_path, namespace)
    sh.run_kubectl(['create', 'namespace', namespace])
    yaml = sh.run(
        ['helm', 'template', chart_path, '--namespace', namespace, *helm_args],
        check=True).stdout
    kubectl.apply_text(yaml, intermediate_file_path=intermediate_file_path)
    wait.until_deployments_are_ready(namespace)


def _parse_known_args() -> Tuple[argparse.Namespace, List[str]]:
    """Parses arch, branch, and log_level into first and rest into second."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--branch', type=str, default=DEFAULT_BRANCH)
    parser.add_argument(
        '--arch',
        type=str,
        choices=['linux', 'osx', 'win'],
        default=DEFAULT_ARCH)
    parser.add_argument(
        '--log_level',
        type=str,
        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
        default='INFO')

    return parser.parse_known_args()


def _log_current_state() -> None:
    logging.info('Kubernetes version:\n%s',
                 sh.run_kubectl(['version'], check=True).stdout)
    logging.info(
        'Pods in istio-system:\n%s',
        sh.run_kubectl(
            [
                '--namespace=istio-system', 'get', 'pods',
                '-o=jsonpath={.items[*].metadata.name}'
            ],
            check=True).stdout)


def main() -> None:
    args, helm_args = _parse_known_args()

    log_level = getattr(logging, args.log_level)
    logging.basicConfig(level=log_level, format='%(levelname)s\t> %(message)s')

    _log_current_state()

    latest_tag = _get_latest_istio_tag(args.branch)

    archive_path = '{}.tar.gz'.format(latest_tag)
    _download_istio_release(latest_tag, args.arch, archive_path)

    extracted_dir_path = latest_tag
    extracted_istio_path = _extract_archive(archive_path, extracted_dir_path)

    chart_path = os.path.join(extracted_istio_path, 'install', 'kubernetes',
                              'helm', 'istio')
    yaml_path = '{}.yaml'.format(latest_tag)
    _apply_template(
        chart_path,
        'istio-system', [*DEFAULT_HELM_ARGS, *helm_args],
        intermediate_file_path=yaml_path)

    # TODO: Wait and watch for 503s/404s for 10m


if __name__ == '__main__':
    main()
