#! /usr/bin/env python3

# -----------------------------------------------------------------------------
# python-template.py Example python skeleton.
# -----------------------------------------------------------------------------

from glob import glob
from urllib.parse import urlparse, urlunparse
import argparse
import json
import linecache
import logging
import os
from pathlib import Path
import shutil
import signal
import stat
import string
import sys
import time

from G2Config import G2Config
from G2ConfigMgr import G2ConfigMgr

try:
    from G2Config import G2Config
    from G2ConfigMgr import G2ConfigMgr
#     from G2Engine import G2Engine
    import G2Exception
except ImportError:
    pass

__all__ = []
__version__ = "1.0.0"  # See https://www.python.org/dev/peps/pep-0396/
__date__ = '2019-07-16'
__updated__ = '2019-08-04'

SENZING_PRODUCT_ID = "5007"  # See https://github.com/Senzing/knowledge-base/blob/master/lists/senzing-product-ids.md
log_format = '%(asctime)s %(message)s'

# Working with bytes.

KILOBYTES = 1024
MEGABYTES = 1024 * KILOBYTES
GIGABYTES = 1024 * MEGABYTES

# Lists from https://www.ietf.org/rfc/rfc1738.txt

safe_character_list = ['$', '-', '_', '.', '+', '!', '*', '(', ')', ',', '"' ] + list(string.ascii_letters)
unsafe_character_list = [ '"', '<', '>', '#', '%', '{', '}', '|', '\\', '^', '~', '[', ']', '`']
reserved_character_list = [ ';', ',', '/', '?', ':', '@', '=', '&']

# The "configuration_locator" describes where configuration variables are in:
# 1) Command line options, 2) Environment variables, 3) Configuration files, 4) Default values

configuration_locator = {
    "config_path": {
        "default": "/etc/opt/senzing",
        "env": "SENZING_CONFIG_PATH",
        "cli": "config-path"
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
    "g2_database_url_generic": {
        "default": "sqlite3://na:na@/var/opt/senzing/sqlite/G2C.db",
        "env": "SENZING_DATABASE_URL",
        "cli": "database-url"
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
    "support_path": {
        "default": "/opt/senzing/data",
        "env": "SENZING_SUPPORT_PATH",
        "cli": "support-path"
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

# Global cached objects

g2_configuration_manager_singleton = None
g2_config_singleton = None

# -----------------------------------------------------------------------------
# Define argument parser
# -----------------------------------------------------------------------------


def get_parser():
    ''' Parse commandline arguments. '''

    subcommands = {
        'initialize': {
            "help": 'Initialize a newly installed Senzing',
            "arguments": {
                "--config-path": {
                    "dest": "config_path",
                    "metavar": "SENZING_CONFIG_PATH",
                    "help": "Location of Senzing's configuration template. Default: /opt/senzing/g2/data"
                },
                "--database-url": {
                    "dest": "g2_database_url_generic",
                    "metavar": "SENZING_DATABASE_URL",
                    "help": "Information for connecting to database."
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
                "--support-path": {
                    "dest": "support_path",
                    "metavar": "SENZING_SUPPORT_PATH",
                    "help": "Location of Senzing's support. Default: /opt/senzing/g2/data"
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
    "155": "{0} - Deleted",
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
    "701": "Error '{0}' caused by {1} error '{2}'",
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
# Database URL parsing
# -----------------------------------------------------------------------------


def translate(map, astring):
    new_string = str(astring)
    for key, value in map.items():
        new_string = new_string.replace(key, value)
    return new_string


def get_unsafe_characters(astring):
    result = []
    for unsafe_character in unsafe_character_list:
        if unsafe_character in astring:
            result.append(unsafe_character)
    return result


def get_safe_characters(astring):
    result = []
    for safe_character in safe_character_list:
        if safe_character not in astring:
            result.append(safe_character)
    return result


def parse_database_url(original_senzing_database_url):
    ''' Given a canonical database URL, decompose into URL components. '''

    result = {}

    # Get the value of SENZING_DATABASE_URL environment variable.

    senzing_database_url = original_senzing_database_url

    # Create lists of safe and unsafe characters.

    unsafe_characters = get_unsafe_characters(senzing_database_url)
    safe_characters = get_safe_characters(senzing_database_url)

    # Detect an error condition where there are not enough safe characters.

    if len(unsafe_characters) > len(safe_characters):
        logging.error(message_error(730, unsafe_characters, safe_characters))
        return result

    # Perform translation.
    # This makes a map of safe character mapping to unsafe characters.
    # "senzing_database_url" is modified to have only safe characters.

    translation_map = {}
    safe_characters_index = 0
    for unsafe_character in unsafe_characters:
        safe_character = safe_characters[safe_characters_index]
        safe_characters_index += 1
        translation_map[safe_character] = unsafe_character
        senzing_database_url = senzing_database_url.replace(unsafe_character, safe_character)

    # Parse "translated" URL.

    parsed = urlparse(senzing_database_url)
    schema = parsed.path.strip('/')

    # Construct result.

    result = {
        'scheme': translate(translation_map, parsed.scheme),
        'netloc': translate(translation_map, parsed.netloc),
        'path': translate(translation_map, parsed.path),
        'params': translate(translation_map, parsed.params),
        'query': translate(translation_map, parsed.query),
        'fragment': translate(translation_map, parsed.fragment),
        'username': translate(translation_map, parsed.username),
        'password': translate(translation_map, parsed.password),
        'hostname': translate(translation_map, parsed.hostname),
        'port': translate(translation_map, parsed.port),
        'schema': translate(translation_map, schema),
    }

    # For safety, compare original URL with reconstructed URL.

    url_parts = [
        result.get('scheme'),
        result.get('netloc'),
        result.get('path'),
        result.get('params'),
        result.get('query'),
        result.get('fragment'),
    ]
    test_senzing_database_url = urlunparse(url_parts)
    if test_senzing_database_url != original_senzing_database_url:
        logging.warning(message_warning(891, original_senzing_database_url, test_senzing_database_url))

    # Return result.

    return result
# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


def get_g2_database_url_specific(generic_database_url):
    ''' Given a canonical database URL, transform to the specific URL. '''

    result = ""
    parsed_database_url = parse_database_url(generic_database_url)
    scheme = parsed_database_url.get('scheme')

    # Format database URL for a particular database.

    if scheme in ['mysql']:
        result = "{scheme}://{username}:{password}@{hostname}:{port}/?schema={schema}".format(**parsed_database_url)
    elif scheme in ['postgresql']:
        result = "{scheme}://{username}:{password}@{hostname}:{port}:{schema}/".format(**parsed_database_url)
    elif scheme in ['db2']:
        result = "{scheme}://{username}:{password}@{schema}".format(**parsed_database_url)
    elif scheme in ['sqlite3']:
        result = "{scheme}://{netloc}{path}".format(**parsed_database_url)
    else:
        logging.error(message_error(695, scheme, generic_database_url))

    return result


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

    # Special case:  Tailored database URL

    result['g2_database_url_specific'] = get_g2_database_url_specific(result.get("g2_database_url_generic"))

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
# Class: G2Client
# -----------------------------------------------------------------------------


class G2Initializer:

    def __init__(self, g2_configuration_manager, g2_config):
        self.g2_config = g2_config
        self.g2_configuration_manager = g2_configuration_manager

    def initialize(self):
        ''' Initialize the G2 database. '''

        # Determine of a default/initial G2 configuration already exists.

        default_config_id_bytearray = bytearray()
        try:
            return_code = self.g2_configuration_manager.getDefaultConfigID(default_config_id_bytearray)
        except Exception as err:
            raise Exception("G2ConfigMgr.getDefaultConfigID({0}) failed".format(default_config_id_bytearray)) from err
        if return_code != 0:
            raise Exception("G2ConfigMgr.getDefaultConfigID({0}) return code {1}".format(default_config_id_bytearray, return_code)) from err

        # If a default configuration exists, there is nothing more to do.

        if default_config_id_bytearray:
            return

        # If there is no default configuration, create one in the 'configuration_bytearray' variable.

        config_handle = self.g2_config.create()

        print("MJD config_handle:  {0}".format(config_handle))

        configuration_bytearray = bytearray()
        try:
            return_code = self.g2_config.save(config_handle, configuration_bytearray)
        except Exception as err:
            raise Exception("G2Confg.save({0}, {1}) failed".format(config_handle, configuration_bytearray)) from err
        if return_code != 0:
            raise Exception("G2Confg.save({0}, {1}) return code {2}".format(config_handle, configuration_bytearray, return_code)) from err

        self.g2_config.close(config_handle)

        # Save configuration JSON into G2 database.

        config_comment = "Initial configuration."
        new_config_id = bytearray()
        try:
            return_code = self.g2_configuration_manager.addConfig(configuration_bytearray.decode(), config_comment, new_config_id)
        except Exception as err:
            raise Exception("G2ConfigMgr.addConfig({0}, {1}, {2}) failed".format(configuration_bytearray.decode(), config_comment, new_config_id)) from err
        if return_code != 0:
            raise Exception("G2ConfigMgr.addConfig({0}, {1}, {2}) return code {3}".format(configuration_bytearray.decode(), config_comment, new_config_id, return_code)) from err

        # Set the default configuration ID.

        try:
            return_code = self.g2_configuration_manager.setDefaultConfigID(new_config_id)
        except Exception as err:
            raise Exception("G2ConfigMgr.setDefaultConfigID({0}) failed".format(new_config_id)) from err
        if return_code != 0:
            raise Exception("G2ConfigMgr.setDefaultConfigID({0}) return code {1}".format(new_config_id, return_code)) from err

# -----------------------------------------------------------------------------
# worker functions
# -----------------------------------------------------------------------------


def change_file_permissions(config):

    # Pull information from config.

    etc_dir = config.get("etc_dir")
    support_path = config.get("support_path")
    var_dir = config.get("var_dir")
    uid = config.get("uid")
    gid = config.get("gid")

    # Identify file changes.

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
        {
            "filename": "{0}/g2config.json".format(etc_dir),
            "permissions": 0o777,
        },
        {
            "filename": "{0}/g2config.json".format(support_path),
            "permissions": 0o777,
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
            requested_file_uid = file.get("uid", 0)
            requested_file_gid = file.get("gid", 0)

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


def copy_files(config):

    # Get paths.

    etc_dir = config.get("etc_dir")
    var_dir = config.get("var_dir")
    support_path = config.get("support_path")

    # Files to copy.

    files = [
        {
            "source_file": "{0}/sqlite/G2C.db".format(var_dir),
            "target_file": "{0}/sqlite/G2C.db.template".format(var_dir),
        },
        {
            "source_file": "{0}/g2config.json".format(etc_dir),
            "target_file": "{0}/g2config.json".format(support_path),
        },
    ]

    # Copy files.

    for file in files:
        target_file = file.get("target_file")
        if not os.path.exists(target_file):
            source_file = file.get("source_file")
            shutil.copyfile(source_file, target_file)
            logging.info(message_info(154, target_file, source_file))


def copy_template_files(config):

    # Review files in "/etc/opt/senzing" directory.

    etc_dir = config.get("etc_dir")
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


def delete_files(config):

    # Get paths.

    etc_dir = config.get("etc_dir")
    support_path = config.get("support_path")

    # Files to copy.

    files = [
        "{0}/g2config.json".format(etc_dir),
        "{0}/g2config.json".format(support_path),
    ]

    # Copy files.

    for file in files:
        if  os.path.exists(file):
            os.remove(file)
            logging.info(message_info(155, file))

# -----------------------------------------------------------------------------
# Senzing services.
# -----------------------------------------------------------------------------


def get_g2_configuration_dictionary(config):
    ''' Construct a dictionary in the form of the old ini files. '''
    result = {
        "PIPELINE": {
            "SUPPORTPATH": config.get("support_path"),
            "CONFIGPATH": config.get("config_path")
        },
        "SQL": {
            "CONNECTION": config.get("g2_database_url_specific"),
        }
    }
    return result


def get_g2_configuration_json(config):
    ''' Return a JSON string with Senzing configuration. '''
    return json.dumps(get_g2_configuration_dictionary(config))


def get_g2_config(config, g2_config_name="init-container-G2-config"):
    ''' Get the G2Config resource. '''
    global g2_config_singleton

    if g2_config_singleton:
        return g2_config_singleton

    try:
        g2_configuration_json = get_g2_configuration_json(config)

        print("MJD g2_configuration_json: {0}".format(g2_configuration_json))

        result = G2Config()
        result.initV2(g2_config_name, g2_configuration_json, config.get('debug', False))
    except G2Exception.G2ModuleException as err:
        exit_error(897, g2_configuration_json, err)

    g2_config_singleton = result
    return result


def get_g2_configuration_manager(config, g2_configuration_manager_name="init-container-G2-configuration-manager"):
    ''' Get the G2ConfigMgr resource. '''
    global g2_configuration_manager_singleton

    if g2_configuration_manager_singleton:
        return g2_configuration_manager_singleton

    try:
        g2_configuration_json = get_g2_configuration_json(config)
        result = G2ConfigMgr()
        result.initV2(g2_configuration_manager_name, g2_configuration_json, config.get('debug', False))
    except G2Exception.G2ModuleException as err:
        exit_error(896, g2_configuration_json, err)

    g2_configuration_manager_singleton = result
    return result

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

    # Manipulate files.

    copy_template_files(config)
    copy_files(config)
    change_file_permissions(config)

    # Get Senzing resources.

    g2_config = get_g2_config(config)
    g2_configuration_manager = get_g2_configuration_manager(config)

    # Initialize G2 database.

    g2_initializer = G2Initializer(g2_configuration_manager, g2_config)
    try:
        g2_initializer.initialize()
    except Exception as err:
        logging.error(message_error(701, err, type(err.__cause__), err.__cause__))

    # Cleanup.

#     delete_files(config)

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
