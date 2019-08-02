#! /usr/bin/env python3

# -----------------------------------------------------------------------------
# python-template.py Example python skeleton.
# -----------------------------------------------------------------------------

from glob import glob
import argparse
import json
import linecache
import logging
import os
from pathlib import Path
import shutil
import signal
import stat
import sys
import time

__all__ = []
__version__ = "1.0.0"  # See https://www.python.org/dev/peps/pep-0396/
__date__ = '2019-07-16'
__updated__ = '2019-08-02'

SENZING_PRODUCT_ID = "5007"  # See https://github.com/Senzing/knowledge-base/blob/master/lists/senzing-product-ids.md
log_format = '%(asctime)s %(message)s'

# Working with bytes.

KILOBYTES = 1024
MEGABYTES = 1024 * KILOBYTES
GIGABYTES = 1024 * MEGABYTES

# The "configuration_locator" describes where configuration variables are in:
# 1) Command line options, 2) Environment variables, 3) Configuration files, 4) Default values

configuration_locator = {
    "data_version_dir": {
        "default": "/opt/senzing/data/1.0.0",
        "env": "SENZING_DATA_VERSION_DIR",
        "cli": "data-version-dir"
    },
    "debug": {
        "default": False,
        "env": "SENZING_DEBUG",
        "cli": "debug"
    },
    "etc_dir": {
        "default": "/etc/opt/senzing",
        "env": "SENZING_ETC_DIR",
        "cli": "etc-dir"
    },
    "g2_dir": {
        "default": "/opt/senzing/g2",
        "env": "SENZING_G2_DIR",
        "cli": "g2-dir"
    },
    "gid": {
        "default": 1001,
        "env": "SENZING_GID",
        "cli": "gid"
    },
    "sleep_time_in_seconds": {
        "default": 0,
        "env": "SENZING_SLEEP_TIME_IN_SECONDS",
        "cli": "sleep-time-in-seconds"
    },
    "subcommand": {
        "default": None,
        "env": "SENZING_SUBCOMMAND",
    },
    "uid": {
        "default": 1001,
        "env": "SENZING_UID",
        "cli": "uid"
    },
    "var_dir": {
        "default": "/var/opt/senzing",
        "env": "SENZING_VAR_DIR",
        "cli": "var-dir"
    },
}

# Enumerate keys in 'configuration_locator' that should not be printed to the log.

keys_to_redact = [
    ]

# -----------------------------------------------------------------------------
# Define argument parser
# -----------------------------------------------------------------------------


def get_parser():
    ''' Parse commandline arguments. '''

    subcommands = {
        'initialize': {
            "help": 'Initialize a newly installed Senzing',
            "arguments": {
                "--data-version-dir": {
                    "dest": "data_version_dir",
                    "metavar": "SENZING_DATA_VERSION_DIR",
                    "help": "Location of senzing data/nn.nn.nn directory. Default: /opt/senzing/data/1.0.0"
                },
                "--debug": {
                    "dest": "debug",
                    "action": "store_true",
                    "help": "Enable debugging. (SENZING_DEBUG) Default: False"
                },
                "--etc-dir": {
                    "dest": "etc_dir",
                    "metavar": "SENZING_ETC_DIR",
                    "help": "Location of senzing etc directory. Default: /etc/opt/senzing"
                },
                "--g2-dir": {
                    "dest": "g2_dir",
                    "metavar": "SENZING_G2_DIR",
                    "help": "Location of senzing g2 directory. Default: /opt/senzing/g2"
                },
                "--gid": {
                    "dest": "gid",
                    "metavar": "SENZING_GID",
                    "help": "GID for file ownership. Default: 1001"
                },
                "--uid": {
                    "dest": "uid",
                    "metavar": "SENZING_UID",
                    "help": "UID for file ownership. Default: 1001"
                },
                "--var-dir": {
                    "dest": "var_dir",
                    "metavar": "SENZING_VAR_DIR",
                    "help": "Location of senzing var directory. Default: /var/opt/senzing"
                },
            },
        },
        'sleep': {
            "help": 'Do nothing but sleep. For Docker testing.',
            "arguments": {
                "--sleep-time-in-seconds": {
                    "dest": "sleep_time_in_seconds",
                    "metavar": "SENZING_SLEEP_TIME_IN_SECONDS",
                    "help": "Sleep time in seconds. DEFAULT: 0 (infinite)"
                },
            },
        },
        'version': {
            "help": 'Print version of program.',
        },
        'docker-acceptance-test': {
            "help": 'For Docker acceptance testing.',
        },
    }

    parser = argparse.ArgumentParser(prog="python-template.py", description="Example python skeleton. For more information, see https://github.com/Senzing/python-template")
    subparsers = parser.add_subparsers(dest='subcommand', help='Subcommands (SENZING_SUBCOMMAND):')

    for subcommand_key, subcommand_values in subcommands.items():
        subcommand_help = subcommand_values.get('help', "")
        subcommand_arguments = subcommand_values.get('arguments', {})
        subparser = subparsers.add_parser(subcommand_key, help=subcommand_help)
        for argument_key, argument_values in subcommand_arguments.items():
            subparser.add_argument(argument_key, **argument_values)

    return parser

# -----------------------------------------------------------------------------
# Message handling
# -----------------------------------------------------------------------------

# 1xx Informational (i.e. logging.info())
# 3xx Warning (i.e. logging.warning())
# 5xx User configuration issues (either logging.warning() or logging.err() for Client errors)
# 7xx Internal error (i.e. logging.error for Server errors)
# 9xx Debugging (i.e. logging.debug())


MESSAGE_INFO = 100
MESSAGE_WARN = 300
MESSAGE_ERROR = 700
MESSAGE_DEBUG = 900

message_dictionary = {
    "100": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}I",
    "151": "{0} - Changed permissions from {1:o} to {2:o}",
    "152": "{0} - Changed owner from {1} to {2}",
    "153": "{0} - Changed group from {1} to {2}",
    "154": "{0} - Created file by copying {1}",
    "292": "Configuration change detected.  Old: {0} New: {1}",
    "293": "For information on warnings and errors, see https://github.com/Senzing/stream-loader#errors",
    "294": "Version: {0}  Updated: {1}",
    "295": "Sleeping infinitely.",
    "296": "Sleeping {0} seconds.",
    "297": "Enter {0}",
    "298": "Exit {0}",
    "299": "{0}",
    "300": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}W",
    "499": "{0}",
    "500": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "695": "Unknown database scheme '{0}' in database url '{1}'",
    "696": "Bad SENZING_SUBCOMMAND: {0}.",
    "697": "No processing done.",
    "698": "Program terminated with error.",
    "699": "{0}",
    "700": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "886": "G2Engine.addRecord() bad return code: {0}; JSON: {1}",
    "887": "G2Engine.addRecord() TranslateG2ModuleException: {0}; JSON: {1}",
    "888": "G2Engine.addRecord() G2ModuleNotInitialized: {0}; JSON: {1}",
    "889": "G2Engine.addRecord() G2ModuleGenericException: {0}; JSON: {1}",
    "890": "G2Engine.addRecord() Exception: {0}; JSON: {1}",
    "891": "Original and new database URLs do not match. Original URL: {0}; Reconstructed URL: {1}",
    "892": "Could not initialize G2Product with '{0}'. Error: {1}",
    "893": "Could not initialize G2Hasher with '{0}'. Error: {1}",
    "894": "Could not initialize G2Diagnostic with '{0}'. Error: {1}",
    "895": "Could not initialize G2Audit with '{0}'. Error: {1}",
    "896": "Could not initialize G2ConfigMgr with '{0}'. Error: {1}",
    "897": "Could not initialize G2Config with '{0}'. Error: {1}",
    "898": "Could not initialize G2Engine with '{0}'. Error: {1}",
    "899": "{0}",
    "900": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}D",
    "901": "{0} will not be modified",
    "999": "{0}",
}


def message(index, *args):
    index_string = str(index)
    template = message_dictionary.get(index_string, "No message for index {0}.".format(index_string))
    return template.format(*args)


def message_generic(generic_index, index, *args):
    index_string = str(index)
    return "{0} {1}".format(message(generic_index, index), message(index, *args))


def message_info(index, *args):
    return message_generic(MESSAGE_INFO, index, *args)


def message_warn(index, *args):
    return message_generic(MESSAGE_WARN, index, *args)


def message_error(index, *args):
    return message_generic(MESSAGE_ERROR, index, *args)


def message_debug(index, *args):
    return message_generic(MESSAGE_DEBUG, index, *args)


def get_exception():
    ''' Get details about an exception. '''
    exception_type, exception_object, traceback = sys.exc_info()
    frame = traceback.tb_frame
    line_number = traceback.tb_lineno
    filename = frame.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, line_number, frame.f_globals)
    return {
        "filename": filename,
        "line_number": line_number,
        "line": line.strip(),
        "exception": exception_object,
        "type": exception_type,
        "traceback": traceback,
    }

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


def get_configuration(args):
    ''' Order of precedence: CLI, OS environment variables, INI file, default. '''
    result = {}

    # Copy default values into configuration dictionary.

    for key, value in list(configuration_locator.items()):
        result[key] = value.get('default', None)

    # "Prime the pump" with command line args. This will be done again as the last step.

    for key, value in list(args.__dict__.items()):
        new_key = key.format(subcommand.replace('-', '_'))
        if value:
            result[new_key] = value

    # Copy OS environment variables into configuration dictionary.

    for key, value in list(configuration_locator.items()):
        os_env_var = value.get('env', None)
        if os_env_var:
            os_env_value = os.getenv(os_env_var, None)
            if os_env_value:
                result[key] = os_env_value

    # Copy 'args' into configuration dictionary.

    for key, value in list(args.__dict__.items()):
        new_key = key.format(subcommand.replace('-', '_'))
        if value:
            result[new_key] = value

    # Special case: subcommand from command-line

    if args.subcommand:
        result['subcommand'] = args.subcommand

    # Special case: Change boolean strings to booleans.

    booleans = ['debug']
    for boolean in booleans:
        boolean_value = result.get(boolean)
        if isinstance(boolean_value, str):
            boolean_value_lower_case = boolean_value.lower()
            if boolean_value_lower_case in ['true', '1', 't', 'y', 'yes']:
                result[boolean] = True
            else:
                result[boolean] = False

    # Special case: Change integer strings to integers.

    integers = [
        'sleep_time_in_seconds'
        ]
    for integer in integers:
        integer_string = result.get(integer)
        result[integer] = int(integer_string)

    return result


def validate_configuration(config):
    ''' Check aggregate configuration from commandline options, environment variables, config files, and defaults. '''

    user_warning_messages = []
    user_error_messages = []

    # Perform subcommand specific checking.

    subcommand = config.get('subcommand')

    if subcommand in ['task1', 'task2']:

        if not config.get('senzing_dir'):
            user_error_messages.append(message_error(414))

    # Log warning messages.

    for user_warning_message in user_warning_messages:
        logging.warning(user_warning_message)

    # Log error messages.

    for user_error_message in user_error_messages:
        logging.error(user_error_message)

    # Log where to go for help.

    if len(user_warning_messages) > 0 or len(user_error_messages) > 0:
        logging.info(message_info(293))

    # If there are error messages, exit.

    if len(user_error_messages) > 0:
        exit_error(597)


def redact_configuration(config):
    ''' Return a shallow copy of config with certain keys removed. '''
    result = config.copy()
    for key in keys_to_redact:
        result.pop(key)
    return result

# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------


def create_signal_handler_function(args):
    ''' Tricky code.  Uses currying technique. Create a function for signal handling.
        that knows about "args".
    '''

    def result_function(signal_number, frame):
        logging.info(message_info(298, args))
        sys.exit(0)

    return result_function


def bootstrap_signal_handler(signal, frame):
    sys.exit(0)


def entry_template(config):
    ''' Format of entry message. '''
    debug = config.get("debug", False)
    config['start_time'] = time.time()
    if debug:
        final_config = config
    else:
        final_config = redact_configuration(config)
    config_json = json.dumps(final_config, sort_keys=True)
    return message_info(297, config_json)


def exit_template(config):
    ''' Format of exit message. '''
    debug = config.get("debug", False)
    stop_time = time.time()
    config['stop_time'] = stop_time
    config['elapsed_time'] = stop_time - config.get('start_time', stop_time)
    if debug:
        final_config = config
    else:
        final_config = redact_configuration(config)
    config_json = json.dumps(final_config, sort_keys=True)
    return message_info(298, config_json)


def exit_error(index, *args):
    ''' Log error message and exit program. '''
    logging.error(message_error(index, *args))
    logging.error(message_error(698))
    sys.exit(1)


def exit_silently():
    ''' Exit program. '''
    sys.exit(1)

# -----------------------------------------------------------------------------
# worker functions
# -----------------------------------------------------------------------------


def copy_template_files(config):

    # Review files in "/etc/opt/senzing" directory.

    etc_dir = config.get("etc_dir")
    var_dir = config.get("var_dir")

    for template_file_name in os.listdir(etc_dir):

        # Process only ".template" files.

        if template_file_name.endswith(".template"):
            template_file_path = os.path.join(etc_dir, template_file_name)
            actual_file_name = Path(template_file_name).stem
            actual_file_path = os.path.join(etc_dir, actual_file_name)

            # If actual file doesn't exist, make it from template file.

            if not os.path.exists(actual_file_path):
                shutil.copyfile(template_file_path, actual_file_path)
                logging.info(message_info(154, actual_file_path, template_file_path))
            else:
                logging.debug(message_debug(901, actual_file_path))

    # Backup files.
    files = [
        {
            "source_file": "{0}/sqlite/G2C.db".format(var_dir),
            "target_file": "{0}/sqlite/G2C.db.template".format(var_dir),
        },
    ]

    for file in files:
        target_file = file.get("target_file")
        if not os.path.exists(target_file):
            source_file = file.get("source_file")
            shutil.copyfile(source_file, target_file)
            logging.info(message_info(154, target_file, source_file))


def change_file_permissions(config):

    var_dir = config.get("var_dir")
    uid = config.get("uid")
    gid = config.get("gid")
    files = [
        {
            "filename": "{0}/sqlite".format(var_dir),
            "permissions": 0o750,
            "uid": uid,
            "gid": gid,
        },
        {
            "filename": "{0}/sqlite/G2C.db".format(var_dir),
            "permissions": 0o750,
            "uid": uid,
            "gid": gid,
        },
        {
            "filename": "{0}/sqlite/G2C.db.template".format(var_dir),
            "permissions": 0o440,
            "uid": uid,
            "gid": gid,
        },
    ]

    # Work through list.

    for file in files:
        filename = file.get("filename")

        # If file exists,

        if os.path.exists(filename):

            # Get actual and requested file metadata.

            actual_file_permissions = os.stat(filename).st_mode & 0o777
            actual_file_uid = os.stat(filename).st_uid
            actual_file_gid = os.stat(filename).st_gid
            requested_file_permissions = file.get("permissions")
            requested_file_uid = file.get("uid")
            requested_file_gid = file.get("gid")

            # Change permissions, if needed.

            if actual_file_permissions != requested_file_permissions:
                os.chmod(filename, requested_file_permissions)
                logging.info(message_info(151, filename, actual_file_permissions, requested_file_permissions))

            # Change ownership, if needed.

            ownership_changed = False
            if actual_file_uid != requested_file_uid:
                ownership_changed = True
                logging.info(message_info(152, filename, actual_file_uid, requested_file_uid))
            if actual_file_gid != requested_file_gid:
                ownership_changed = True
                logging.info(message_info(153, filename, actual_file_gid, requested_file_gid))
            if ownership_changed:
                os.chown(filename, requested_file_uid, requested_file_gid)

# -----------------------------------------------------------------------------
# do_* functions
#   Common function signature: do_XXX(args)
# -----------------------------------------------------------------------------


def do_docker_acceptance_test(args):
    ''' For use with Docker acceptance testing. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)

    # Prolog.

    logging.info(entry_template(config))

    # Epilog.

    logging.info(exit_template(config))


def do_initialize(args):
    ''' Do a task. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)

    # Prolog.

    logging.info(entry_template(config))

    # FIXME: Copy template files.

    copy_template_files(config)
    change_file_permissions(config)

    # FIXME: Prime G2 database SYS_CFG and SYS_VAR tables

    # Epilog.

    logging.info(exit_template(config))


def do_sleep(args):
    ''' Sleep.  Used for debugging. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)

    # Prolog.

    logging.info(entry_template(config))

    # Pull values from configuration.

    sleep_time_in_seconds = config.get('sleep_time_in_seconds')

    # Sleep

    if sleep_time_in_seconds > 0:
        logging.info(message_info(296, sleep_time_in_seconds))
        time.sleep(sleep_time_in_seconds)

    else:
        sleep_time_in_seconds = 3600
        while True:
            logging.info(message_info(295))
            time.sleep(sleep_time_in_seconds)

    # Epilog.

    logging.info(exit_template(config))


def do_version(args):
    ''' Log version information. '''

    logging.info(message_info(294, __version__, __updated__))

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


if __name__ == "__main__":

    # Configure logging. See https://docs.python.org/2/library/logging.html#levels

    log_level_map = {
        "notset": logging.NOTSET,
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "fatal": logging.FATAL,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }

    log_level_parameter = os.getenv("SENZING_LOG_LEVEL", "info").lower()
    log_level = log_level_map.get(log_level_parameter, logging.INFO)
    logging.basicConfig(format=log_format, level=log_level)

    # Trap signals temporarily until args are parsed.

    signal.signal(signal.SIGTERM, bootstrap_signal_handler)
    signal.signal(signal.SIGINT, bootstrap_signal_handler)

    # Parse the command line arguments.

    subcommand = os.getenv("SENZING_SUBCOMMAND", None)
    parser = get_parser()
    if len(sys.argv) > 1:
        args = parser.parse_args()
        subcommand = args.subcommand
    elif subcommand:
        args = argparse.Namespace(subcommand=subcommand)
    else:
        parser.print_help()
        if len(os.getenv("SENZING_DOCKER_LAUNCHED", "")):
            subcommand = "sleep"
            args = argparse.Namespace(subcommand=subcommand)
            do_sleep(args)
        exit_silently()

    # Catch interrupts. Tricky code: Uses currying.

    signal_handler = create_signal_handler_function(args)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Transform subcommand from CLI parameter to function name string.

    subcommand_function_name = "do_{0}".format(subcommand.replace('-', '_'))

    # Test to see if function exists in the code.

    if subcommand_function_name not in globals():
        logging.warning(message_warning(596, subcommand))
        parser.print_help()
        exit_silently()

    # Tricky code for calling function based on string.

    globals()[subcommand_function_name](args)
