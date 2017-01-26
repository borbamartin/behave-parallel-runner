"""

------------------------------
BEHAVE PARALLEL FEATURE RUNNER
------------------------------

This module provides functionality to run Behave features in parallel.

The amount of features that will run in parallel is determined by
MAX_WORKERS environment variable, set to a default value when not specified.

    Command line usage:
        behave_parallel_runner <tag_args> <feature_args>

    Accepted args:
        <tag_args>
            * --tags=some_tag (same as 'behave' command)

        <feature_args>
            * Single path to a features directory
            * Single path to a feature file
            * Multiple paths to different feature files

    Usage examples:
        * behave_parallel_runner --tags=test ui_tests/admin/features
        * behave_parallel_runner --tags=test ui_tests/admin/features/health.feature
        * behave_parallel_runner --tags=test ui_tests/admin/features/health.feature
            ui_tests/admin/features/apigee.feature

"""
import copy
import gc
import os
import subprocess
import sys
import time

from havanna.datetime_utils import DateTimeUtil

__author__ = 'Martin Borba - borbamartin@gmail.com'

MAX_WORKERS = 0
active_workers = []

base_command = 'behave -k --junit --tags=-wip {} {}'
tags = []
feature_args = []

dtu = DateTimeUtil(display_seconds=True)


class Worker(object):
    """
    This class represents a subprocess worker
    """

    def __init__(self, file_path):
        """
        Initialize a Worker instance

        :param file_path:
            A string representing the file path

        """
        self.file_path = file_path
        self.subprocess = None
        self.log_file = None

    @property
    def file_name(self):
        fp = self.file_path
        return fp[fp.rfind(os.sep):fp.rfind('.')]


def _set_max_workers():
    """
    Sets the max amount of workers available for the current execution
    Default value will be used if MAX_WORKERS environment variable is not specified
    """
    global MAX_WORKERS
    MAX_WORKERS = int(os.getenv('BEHAVE_MAX_WORKERS', 3))

    _log('Enabled {} workers'.format(MAX_WORKERS))


def _log(msg):
    """
    Log a message into the behave parallel runner default output

    :param msg:
        A string representing the message to _log
    """
    dtu.refresh()
    print('[behave-parallel-runner @ {}] {}'.format(dtu.time24, msg))


def _parse_args():
    """
    Parses the arguments provided to the behave parallel runner script
    """
    _log('Parsing script arguments')
    args = copy.copy(sys.argv)
    args.pop(0)  # Remove Python file path arg

    for arg in args:
        if arg[:7] == '--tags=':
            tags.append(arg)
        else:
            feature_args.append(arg)

    assert len(feature_args) > 0, 'Feature file/directory path not specified'


def _unify_tags():
    """
    Converts the tags list to a single string
    """
    global tags

    if tags:
        tags_as_str = ''
        _log('Unifying tags')

        for tag in tags:
            tags_as_str = ' '.join((tags_as_str, tag))

        tags = tags_as_str.strip()
    else:
        tags = ''


def _validate_feature_args():
    """
    Validates the given feature arguments

    Accepted args are:
        * Single path to a features directory
        * Single path to a feature file
        * Multiple paths to different feature files
    """
    assert_features_only = False

    if len(feature_args) > 1:
        # If multiple feature args are received
        # then all args must be files, not dirs
        assert_features_only = True

    for arg in feature_args:
        if not os.path.exists(arg):
            raise Exception('"{}" is not a valid feature/dir path'.format(arg))

        if assert_features_only:
            assert os.path.isfile(arg), "Please specify multiple features' file path " \
                                        "or a single path to a directory of features"


def _list_features_in_dir(features_dir_path):
    """
    Scans a directory for feature files

    :param features_dir_path:
        A string representing the features directory path

    :returns:
        A list of feature files (relative path & filename)
    """
    feature_list = []

    if features_dir_path.endswith(os.path.sep):
        features_dir_path = features_dir_path[:-1]

    for _file in os.listdir(features_dir_path):
        if _file.endswith('.feature'):
            feature_path = os.path.sep.join((features_dir_path, _file))
            feature_list.append(feature_path)

    return feature_list


def _list_features():
    """
    Builds a list of features to be executed

    :returns:
        A list of features (relative path & filename)
    """
    _log('Listing features')
    _validate_feature_args()
    feature_list = []

    if len(feature_args) == 1:
        # If single feature arg is specified
        feature_arg = feature_args[0]

        if os.path.isdir(feature_arg):
            # If the feature arg is a directory
            feature_list = _list_features_in_dir(feature_arg)
        elif os.path.isfile(feature_arg):
            # If the feature arg is a file
            feature_list.append(feature_arg)
        else:
            raise Exception('"{}" is not a valid feature/dir path'.format(feature_arg))

    else:
        feature_list = feature_args

    return feature_list


def _trigger_feature(feature_path):
    """
    Triggers a feature execution

    :param feature_path:
        A string representing the feature (relative path & filename)
    """
    _log('Triggering feature: "{}"'.format(feature_path))

    worker = Worker(feature_path)

    log_file_name = '{}{}{}'.format(os.getcwd(), worker.file_name, '.log')
    log_file = open(log_file_name, "w+")

    cmd = base_command.format(tags, feature_path)
    process = subprocess.Popen(cmd, shell=True, stdout=log_file, stderr=log_file)

    worker.log_file = log_file
    worker.subprocess = process
    active_workers.append(worker)


def main():
    """
    Behave Parallel Runner main process
    """
    print('\nBEHAVE PARALLEL RUNNER\n')

    dtu.refresh()
    start_date = dtu.stored_time

    _log('Execution started @ {} EST'.format(dtu.timestamp24))

    _set_max_workers()
    _parse_args()
    _unify_tags()

    feature_list = _list_features()
    are_active_workers = True

    while are_active_workers:
        for worker in active_workers:
            if worker.subprocess.poll() is not None:
                # If the worker subprocess finished
                # Remove worker
                _log('Releasing worker')
                active_workers.remove(worker)
                worker.log_file.close()

                # Print feature log
                _log('{} output:\n'.format('.'.join((worker.file_name, 'feature'))))
                log_file = open(worker.log_file.name, 'r')
                print(log_file.read())

                # Remove feature log file
                log_file.close()
                os.remove(worker.log_file.name)

                # Delete worker and call garbage collector
                del worker
                gc.collect()

        if len(feature_list) > 0 and len(active_workers) < MAX_WORKERS:
            # If there's pending features
            # And there's an available worker
            # Trigger another feature
            feature = feature_list.pop(0)
            _trigger_feature(feature)

        if len(feature_list) == 0 and len(active_workers) == 0:
            # If no feature's pending
            # And there are no active workers
            # Terminate the execution
            are_active_workers = False

    dtu.refresh()
    end_date = dtu.stored_time
    took = time.strftime('%Hh %Mm %Ss', time.gmtime((end_date - start_date).total_seconds()))

    _log('Execution finished @ {} EST'.format(dtu.timestamp24))
    _log('Took {}'.format(took))
