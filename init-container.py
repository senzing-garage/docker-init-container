#! /usr/bin/env python3

# -----------------------------------------------------------------------------
# init-container.py Example python skeleton.
# -----------------------------------------------------------------------------

from pathlib import Path
from urllib.parse import urlparse, urlunparse
import argparse
import base64
import configparser
import filecmp
import json
import linecache
import logging
import os
import shutil
import signal
import stat
import string
import sys
import time
import urllib
import urllib.request

try:
    from G2Config import G2Config
    from G2ConfigMgr import G2ConfigMgr
    import G2Exception
except ImportError:
    pass

__all__ = []
__version__ = "1.6.8"  # See https://www.python.org/dev/peps/pep-0396/
__date__ = '2019-07-16'
__updated__ = '2021-03-31'

SENZING_PRODUCT_ID = "5007"  # See https://github.com/Senzing/knowledge-base/blob/master/lists/senzing-product-ids.md
log_format = '%(asctime)s %(message)s'

# Working with bytes.

KILOBYTES = 1024
MEGABYTES = 1024 * KILOBYTES
GIGABYTES = 1024 * MEGABYTES

# Lists from https://www.ietf.org/rfc/rfc1738.txt

safe_character_list = ['$', '-', '_', '.', '+', '!', '*', '(', ')', ',', '"'] + list(string.ascii_letters)
unsafe_character_list = ['"', '<', '>', '#', '%', '{', '}', '|', '\\', '^', '~', '[', ']', '`']
reserved_character_list = [';', ',', '/', '?', ':', '@', '=', '&']

# The "configuration_locator" describes where configuration variables are in:
# 1) Command line options, 2) Environment variables, 3) Configuration files, 4) Default values

configuration_locator = {
    "data_dir": {
        "default": "/opt/senzing/data",
        "env": "SENZING_DATA_DIR",
        "cli": "data-dir"
    },
    "db2dsdriver_cfg_contents": {
        "default": None,
        "env": "SENZING_OPT_IBM_DB2_CLIDRIVER_CFG_DB2DSDRIVER_CFG_CONTENTS",
        "cli": "db2dsdriver-cfg-contents"
    },
    "debug": {
        "default": False,
        "env": "SENZING_DEBUG",
        "cli": "debug"
    },
    "delay_in_seconds": {
        "default": 0,
        "env": "SENZING_DELAY_IN_SECONDS",
        "cli": "delay-in-seconds"
    },
    "etc_dir": {
        "default": "/etc/opt/senzing",
        "env": "SENZING_ETC_DIR",
        "cli": "etc-dir"
    },
    "enable_db2": {
        "default": False,
        "env": "SENZING_ENABLE_DB2",
        "cli": "enable-db2"
    },
    "enable_mssql": {
        "default": False,
        "env": "SENZING_ENABLE_MSSQL",
        "cli": "enable-mssql"
    },
    "enable_mysql": {
        "default": False,
        "env": "SENZING_ENABLE_MYSQL",
        "cli": "enable-mysql"
    },
    "enable_postgresql": {
        "default": False,
        "env": "SENZING_ENABLE_POSTGRESQL",
        "cli": "enable-postgresql"
    },
    "engine_configuration_json": {
        "default": None,
        "env": "SENZING_ENGINE_CONFIGURATION_JSON",
        "cli": "engine-configuration-json"
    },
    "g2_config_gtc": {
        "default": None,
        "env": "SENZING_G2CONFIG_GTC",
        "cli": "g2config-gtc"
    },
    "g2_database_url": {
        "default": "sqlite3://na:na@/var/opt/senzing/sqlite/G2C.db",
        "env": "SENZING_DATABASE_URL",
        "cli": "database-url"
    },
    "g2_database_url_raw": {
        "default": None,
        "env": "SENZING_DATABASE_URL_RAW",
        "cli": "database-url-raw"
    },
    "g2_dir": {
        "default": "/opt/senzing/g2",
        "env": "SENZING_G2_DIR",
        "cli": "g2-dir"
    },
    "governor_url": {
        "default": "https://raw.githubusercontent.com/Senzing/governor-postgresql-transaction-id/master/senzing_governor.py",
        "env": "SENZING_GOVERNOR_URL",
        "cli": "governor-url"
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
    "license_base64_encoded": {
        "default": None,
        "env": "SENZING_LICENSE_BASE64_ENCODED",
        "cli": "license-base64-encoded"
    },
    "api_server_key_store_base64_encoded": {
        "default": None,
        "env": "SENZING_API_SERVER_KEY_STORE_BASE64_ENCODED",
        "cli": "api-server-key-store-base64-encoded"
    },
    "api_server_client_key_store_base64_encoded": {
        "default": None,
        "env": "SENZING_API_SERVER_CLIENT_KEY_STORE_BASE64_ENCODED",
        "cli": "api-server-client-key-store-base64-encoded"
    },
    "mssql_odbc_ini_contents": {
        "default": None,
        "env": "SENZING_OPT_MICROSOFT_MSODBCSQL17_ETC_ODBC_INI_CONTENTS",
        "cli": "mssql-odbc-ini-contents"
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
    "update_ini_files": {
        "default": False,
        "env": "SENZING_UPDATE_INI_FILES",
        "cli": "update-ini-files"
    },
    "var_dir": {
        "default": "/var/opt/senzing",
        "env": "SENZING_VAR_DIR",
        "cli": "var-dir"
    },
}

# Enumerate keys in 'configuration_locator' that should not be printed to the log.

keys_to_redact = [
    "engine_configuration_json",
    "g2_database_url",
    "g2_database_url_raw",
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
        'debug-database-url': {
            "help": 'Show parsed database URL.  Does not modify system.',
            "argument_aspects": ["common"],
        },
        'initialize': {
            "help": 'Initialize a newly installed Senzing',
            "argument_aspects": ["common", "senzing-volumes", "enable", "uidgid"],
        },
        'initialize-database': {
            "help": 'Initialize only the database. This is a subset of the full initialize sub-commmand',
            "argument_aspects": ["common", "senzing-volumes"],
            "arguments": {
                "--update-ini-files": {
                    "dest": "update_ini_files",
                    "action": "store_true",
                    "help": "Update INI files: G2Module.ini, (SENZING_UPDATE_INI_FILES) Default: False"
                },
            },
        },
        'initialize-files': {
            "help": 'Initialize only the files. This is a subset of the full initialize sub-commmand',
            "argument_aspects": ["common", "senzing-volumes", "enable", "uidgid"],
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

    # Define argument_aspects.

    argument_aspects = {
        "common": {
            "--database-url": {
                "dest": "g2_database_url",
                "metavar": "SENZING_DATABASE_URL",
                "help": "Information for connecting to database."
            },
            "--debug": {
                "dest": "debug",
                "action": "store_true",
                "help": "Enable debugging. (SENZING_DEBUG) Default: False"
            },
            "--delay-in-seconds": {
                "dest": "delay_in_seconds",
                "metavar": "SENZING_DELAY_IN_SECONDS",
                "help": "Delay before processing in seconds. DEFAULT: 0"
            },
            "--engine-configuration-json": {
                "dest": "engine_configuration_json",
                "metavar": "SENZING_ENGINE_CONFIGURATION_JSON",
                "help": "Advanced Senzing engine configuration. Default: none"
            },
            "--db2dsdriver-cfg-contents": {
                "dest": "db2dsdriver_cfg_contents",
                "metavar": "SENZING_OPT_IBM_DB2_CLIDRIVER_CFG_DB2DSDRIVER_CFG_CONTENTS",
                "help": "Contents of the Db2 db2dsdriver.cfg file for advanced Db2 configurations or Senzing Clustering. Default: none"
            },
            "--mssql-odbc-ini-contents": {
                "dest": "mssql_odbc_ini_contents",
                "metavar": "SENZING_OPT_MICROSOFT_MSODBCSQL17_ETC_ODBC_INI_CONTENTS",
                "help": "Contents of the odbc.ini file when used with mssql. Default: none"
            },
        },
        "enable": {
            "--enable-db2": {
                "dest": "enable_db2",
                "action": "store_true",
                "help": "Enable db2 database. (SENZING_ENABLE_DB2) Default: False"
            },
            "--enable-mssql": {
                "dest": "enable_mssql",
                "action": "store_true",
                "help": "Enable MS SQL database. (SENZING_ENABLE_MSSQL) Default: False"
            },
            "--enable-mysql": {
                "dest": "enable_mysql",
                "action": "store_true",
                "help": "Enable MySQL database. (SENZING_ENABLE_MYSQL) Default: False"
            },
            "--enable-postgresql": {
                "dest": "enable_postgresql",
                "action": "store_true",
                "help": "Enable PostgreSQL database. (SENZING_ENABLE_POSTGRESQL) Default: False"
            },
        },
        "senzing-volumes": {
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
            "--data-dir": {
                "dest": "data_dir",
                "metavar": "SENZING_DATA_DIR",
                "help": "Location of Senzing's support. Default: /opt/senzing/g2/data"
            },
            "--var-dir": {
                "dest": "var_dir",
                "metavar": "SENZING_VAR_DIR",
                "help": "Location of senzing var directory. Default: /var/opt/senzing"
            },
        },
        "uidgid": {
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
        },
    }

    # Augment "subcommands" variable with arguments specified by aspects.

    for subcommand, subcommand_value in subcommands.items():
        if 'argument_aspects' in subcommand_value:
            for aspect in subcommand_value['argument_aspects']:
                if 'arguments' not in subcommands[subcommand]:
                    subcommands[subcommand]['arguments'] = {}
                arguments = argument_aspects.get(aspect, {})
                for argument, argument_value in arguments.items():
                    subcommands[subcommand]['arguments'][argument] = argument_value

    parser = argparse.ArgumentParser(prog="init-container.py", description="Initialize Senzing installation. For more information, see https://github.com/Senzing/docker-init-container")
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
    "151": "{0} - Changing permissions from {1:o} to {2:o}",
    "152": "{0} - Changing owner from {1} to {2}",
    "153": "{0} - Changing group from {1} to {2}",
    "154": "{0} - Creating file by copying {1}",
    "155": "{0} - Deleting",
    "156": "{0} - Modified. {1}",
    "157": "{0} - Creating file",
    "158": "{0} - Creating symlink to {1}",
    "159": "{0} - Downloading from {1}",
    "160": "{0} - Copying {1} and modifying",
    "161": "{0} - Backup of current {1}",
    "162": "{0} - Creating directory",
    "163": "{0} - Configuring for Senzing database cluster based on SENZING_ENGINE_CONFIGURATION_JSON",
    "170": "Created new default config in SYS_CFG having ID {0}",
    "171": "Default config in SYS_CFG already exists having ID {0}",
    "180": "{0} - Postgresql detected.  Installing governor from {1}",
    "181": "{0} - Postgresql detected. Using existing governor; no change.",
    "182": "Initializing for SQLite",
    "183": "Initializing for Db2",
    "184": "Initializing for MS SQL",
    "185": "Initializing for MySQL",
    "186": "Initializing for PostgreSQL",
    "292": "Configuration change detected.  Old: {0} New: {1}",
    "293": "For information on warnings and errors, see https://github.com/Senzing/stream-loader#errors",
    "294": "Version: {0}  Updated: {1}",
    "295": "Sleeping infinitely.",
    "296": "Sleeping {0} seconds.",
    "297": "Enter {0}",
    "298": "Exit {0}",
    "299": "{0}",
    "300": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}W",
    "301": "Could not download the senzing postgresql governor from {0}. Ignore this on air gapped systems. Exception details: {1}",
    "499": "{0}",
    "500": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "510": "{0} - File is missing.",
    "695": "Unknown database scheme '{0}' in database url '{1}'",
    "696": "Bad SENZING_SUBCOMMAND: {0}.",
    "697": "No processing done.",
    "698": "Program terminated with error.",
    "699": "{0}",
    "700": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "701": "Error '{0}' caused by {1} error '{2}'",
    "702": "Could not create '{0}' directory. Error: {1}",
    "703": "SENZING_ENGINE_CONFIGURATION_JSON specified but not SENZING_OPT_IBM_DB2_CLIDRIVER_CFG_DB2DSDRIVER_CFG_CONTENTS. If the Senzing engine config is specified, the contents of db2dsdriver.cfg must also be provided.",
    "704": "SENZING_ENGINE_CONFIGURATION_JSON specified but not SENZING_OPT_MICROSOFT_MSODBCSQL17_ETC_ODBC_INI_CONTENTS. If the Senzing engine config is specified, the contents of odbc.ini must also be provided.",
    "801": "SENZING_ENGINE_CONFIGURATION_JSON contains multiple database schemes: {0}",
    "886": "G2Engine.addRecord() bad return code: {0}; JSON: {1}",
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
    "902": "{0} - Was not created because there is no {1}",
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


def message_warning(index, *args):
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


def parse_database_url_scheme(senzing_database_url):
    return senzing_database_url.split(':')[0]

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


def get_g2_database_url_raw(generic_database_url):
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
    elif scheme in ['mssql']:
        result = "{scheme}://{username}:{password}@{schema}".format(**parsed_database_url)
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

    # Add program information.

    result['program_version'] = __version__
    result['program_updated'] = __updated__

    # Special case: subcommand from command-line

    if args.subcommand:
        result['subcommand'] = args.subcommand

    # Special case: Change boolean strings to booleans.

    booleans = [
        'debug',
        'enable_db2'
        'enable_mssql',
        'enable_mysql',
        'enable_postgresql',
        'update_ini_files',
    ]
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
        'delay_in_seconds',
        'sleep_time_in_seconds',
        ]
    for integer in integers:
        integer_string = result.get(integer)
        result[integer] = int(integer_string)

    # Special case:  Tailored database URL

    if not result['g2_database_url_raw']:
        result['g2_database_url_raw'] = get_g2_database_url_raw(result.get("g2_database_url"))

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


def delay(config):
    delay_in_seconds = config.get('delay_in_seconds')
    if delay_in_seconds > 0:
        logging.info(message_info(296, delay_in_seconds))
        time.sleep(delay_in_seconds)


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

    def create_default_config_id(self):
        ''' Initialize the G2 database. '''

        # Determine of a default/initial G2 configuration already exists.

        default_config_id_bytearray = bytearray()
        try:
            self.g2_configuration_manager.getDefaultConfigID(default_config_id_bytearray)
        except Exception as err:
            raise Exception("G2ConfigMgr.getDefaultConfigID({0}) failed".format(default_config_id_bytearray)) from err

        # If a default configuration exists, there is nothing more to do.

        if default_config_id_bytearray:
            logging.info(message_info(171, default_config_id_bytearray.decode()))
            return None

        # If there is no default configuration, create one in the 'configuration_bytearray' variable.

        config_handle = self.g2_config.create()
        configuration_bytearray = bytearray()
        try:
            self.g2_config.save(config_handle, configuration_bytearray)
        except Exception as err:
            raise Exception("G2Confg.save({0}, {1}) failed".format(config_handle, configuration_bytearray)) from err

        self.g2_config.close(config_handle)

        # Save configuration JSON into G2 database.

        config_comment = "Initial configuration."
        new_config_id = bytearray()
        try:
            self.g2_configuration_manager.addConfig(configuration_bytearray.decode(), config_comment, new_config_id)
        except Exception as err:
            raise Exception("G2ConfigMgr.addConfig({0}, {1}, {2}) failed".format(configuration_bytearray.decode(), config_comment, new_config_id)) from err

        # Set the default configuration ID.

        try:
            self.g2_configuration_manager.setDefaultConfigID(new_config_id)
        except Exception as err:
            raise Exception("G2ConfigMgr.setDefaultConfigID({0}) failed".format(new_config_id)) from err

        return new_config_id

# -----------------------------------------------------------------------------
# worker functions
# -----------------------------------------------------------------------------


def change_directory_ownership(config):

    etc_dir = config.get("etc_dir")
    var_dir = config.get("var_dir")
    uid = config.get("uid")
    gid = config.get("gid")

    directories = [
        etc_dir,
        var_dir,
        "/opt/microsoft/msodbcsql17/etc/",
        "/opt/IBM/db2/clidriver/cfg/"
    ]

    for directory in directories:
        if os.path.isdir(directory):
            actual_uid = os.stat(directory).st_uid
            actual_gid = os.stat(directory).st_gid

            if (actual_uid, actual_gid) != (uid, gid):
                logging.info(message_info(152, directory, "{0}:{1}".format(actual_uid, actual_gid), "{0}:{1}".format(uid, gid)))
                os.chown(directory, int(uid), int(gid))

            for root, dirs, files in os.walk(directory):
                for dir in dirs:
                    dirname = os.path.join(root, dir)
                    actual_uid = os.stat(dirname).st_uid
                    actual_gid = os.stat(dirname).st_gid
                    if (actual_uid, actual_gid) != (uid, gid):
                        logging.info(message_info(152, dirname, "{0}:{1}".format(actual_uid, actual_gid), "{0}:{1}".format(uid, gid)))
                        os.chown(dirname, int(uid), int(gid))

                for file in files:
                    filename = os.path.join(root, file)
                    actual_uid = os.stat(filename).st_uid
                    actual_gid = os.stat(filename).st_gid
                    if (actual_uid, actual_gid) != (uid, gid):
                        logging.info(message_info(152, filename, "{0}:{1}".format(actual_uid, actual_gid), "{0}:{1}".format(uid, gid)))
                        os.chown(filename, int(uid), int(gid))


def change_file_permissions(config):

    # Pull information from config.

    etc_dir = config.get("etc_dir")
    var_dir = config.get("var_dir")
    uid = config.get("uid")
    gid = config.get("gid")

    # Identify file changes.

    files = [
        {
            "filename": "{0}/G2Module.ini".format(etc_dir),
            "permissions": 0o750,
            "uid": uid,
            "gid": gid,
        },
        {
            "filename": "{0}/G2Project.ini".format(etc_dir),
            "permissions": 0o750,
            "uid": uid,
            "gid": gid,
        },
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
            "filename": "{0}/sqlite/G2C_LIBFEAT.db".format(var_dir),
            "permissions": 0o750,
            "uid": uid,
            "gid": gid,
        },
        {
            "filename": "{0}/sqlite/G2C_RES.db".format(var_dir),
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
            "filename": "/opt/microsoft/msodbcsql17/etc/odbc.ini",
            "permissions": 0o750,
            "uid": uid,
            "gid": gid,
        },
        {
            "filename": "/opt/IBM/db2/clidriver/cfg/db2dsdriver.cfg",
            "permissions": 0o755,
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
            requested_file_uid = file.get("uid", 0)
            requested_file_gid = file.get("gid", 0)

            # Change permissions, if needed.

            if actual_file_permissions != requested_file_permissions:
                logging.info(message_info(151, filename, actual_file_permissions, requested_file_permissions))
                os.chmod(filename, requested_file_permissions)

            # Change ownership, if needed.

            ownership_changed = False
            if actual_file_uid != requested_file_uid:
                ownership_changed = True
                logging.info(message_info(152, filename, actual_file_uid, requested_file_uid))
            if actual_file_gid != requested_file_gid:
                ownership_changed = True
                logging.info(message_info(153, filename, actual_file_gid, requested_file_gid))
            if ownership_changed:
                os.chown(filename, int(requested_file_uid), int(requested_file_gid))


def change_module_ini(config):

    etc_dir = config.get("etc_dir")
    new_database_url = config.get('g2_database_url_raw')
    engine_configuration_json = config.get('engine_configuration_json')

    # Read G2Module.ini.

    filename = "{0}/G2Module.ini".format(etc_dir)
    config_parser = configparser.ConfigParser()
    config_parser.optionxform = str  # Maintain case of keys.
    config_parser.read(filename)

    # If configuration was passed in via SENZING_ENGINE_CONFIGURATION_JSON, do a straight conversion to ini

    if engine_configuration_json:
        logging.info(message_info(163, filename))
        engine_configuration = json.loads(engine_configuration_json)

        for key, value in engine_configuration.items():
            config_parser[key] = value

    else:
        # Check SQL.CONNECTION.

        old_database_url = config_parser.get('SQL', 'CONNECTION')
        if new_database_url != old_database_url:
            config_parser['SQL']['CONNECTION'] = new_database_url
            message = "Changed SQL.CONNECTION to {0}".format(new_database_url)
            logging.info(message_info(156, filename, message))

        # Update PIPELINE entires - These are hard coded because they are always the same inside the conainter, but can be overridden by SENZING_ENGINE_CONFIGURATION_JSON
        config_parser['PIPELINE']['SUPPORTPATH'] = '/opt/senzing/data'
        message = "Changed PIPELINE.SUPPORTPATH to /opt/senzing/data"
        logging.info(message_info(156, filename, message))

        config_parser['PIPELINE']['CONFIGPATH'] = '/etc/opt/senzing'
        message = "Changed PIPELINE.CONFIGPATH to /etc/opt/senzing"
        logging.info(message_info(156, filename, message))

        config_parser['PIPELINE']['RESOURCEPATH'] = '/opt/senzing/g2/resources'
        message = "Changed PIPELINE.RESOURCEPATH to /opt/senzing/g2/resources"
        logging.info(message_info(156, filename, message))

        # Remove SQL.G2CONFIGFILE option.

        config_parser.remove_option('SQL', 'G2CONFIGFILE')
        message = "Removed SQL.G2CONFIGFILE"
        logging.info(message_info(156, filename, message))

    # Write out contents.

    with open(filename, 'w') as output_file:
        config_parser.write(output_file)


def change_project_ini(config):

    etc_dir = config.get("etc_dir")
    new_database_url = config.get('g2_database_url_raw')

    # Read G2Project.ini.

    filename = "{0}/G2Project.ini".format(etc_dir)

    # As of Senzing 2.3.0 this file doesn't exist.

    if not os.path.exists(filename):
        return

    # Parse the ini file.

    config_parser = configparser.ConfigParser()
    config_parser.optionxform = str  # Maintain case of keys
    config_parser.read(filename)

    # Used to remember if contents change.

    changed = False

    # Check SQL.CONNECTION.

    old_database_url = config_parser.get('g2', 'G2Connection')
    if new_database_url != old_database_url:
        changed = True
        config_parser['g2']['G2Connection'] = new_database_url
        message = "Changed g2.G2Connection to {0}".format(new_database_url)
        logging.info(message_info(156, filename, message))

    # Write out contents.

    if changed:
        with open(filename, 'w') as output_file:
            config_parser.write(output_file)


def copy_files(config):

    # Get paths.

    etc_dir = config.get("etc_dir")
    g2_dir = config.get("g2_dir")
    var_dir = config.get("var_dir")

    # Files to copy.

    template_file_names_2_0 = [
        "cfgVariant.json",
        "customOn.txt",
        "defaultGNRCP.config",
        "g2config.json",
        "G2Project.ini",
        "customGn.txt",
        "customSn.txt",
        "G2Module.ini",
        "stb.config",
    ]

    template_file_names_1_x = [
        "cfgVariant.json.template",
        "customOn.txt.template",
        "defaultGNRCP.config.template",
        "g2config.json.template",
        "G2Project.ini.template",
        "customGn.txt.template",
        "customSn.txt.template",
        "G2Module.ini.template",
        "stb.config.template",
    ]

    # Append files from various places.

    files = [
        {
            "source_file": "{0}/sqlite/G2C.db".format(var_dir),
            "target_file": "{0}/sqlite/G2C.db.template".format(var_dir),
        }, {
            "source_file": "{0}/resources/templates/G2C.db".format(g2_dir),
            "target_file": "{0}/sqlite/G2C.db".format(var_dir),
        }, {
            "source_file": "{0}/resources/templates/G2C.db".format(g2_dir),
            "target_file": "{0}/sqlite/G2C_LIBFEAT.db".format(var_dir),
        }, {
            "source_file": "{0}/resources/templates/G2C.db".format(g2_dir),
            "target_file": "{0}/sqlite/G2C_RES.db".format(var_dir),
        }, {
            "source_file": "{0}/resources/templates/G2C.db.template".format(g2_dir),
            "target_file": "{0}/sqlite/G2C.db".format(var_dir),
        }, {
            "source_file": "{0}/resources/templates/G2C.db.template".format(g2_dir),
            "target_file": "{0}/sqlite/G2C_LIBFEAT.db".format(var_dir),
        }, {
            "source_file": "{0}/resources/templates/G2C.db.template".format(g2_dir),
            "target_file": "{0}/sqlite/G2C_RES.db".format(var_dir),
        }
    ]

    # Add files from {resource_dir}/templates

    for template_file_name in template_file_names_2_0:

        # Handle files from 2.0+

        from_templates = {
            "source_file": "{0}/resources/templates/{1}".format(g2_dir, template_file_name),
            "target_file": "{0}/{1}".format(etc_dir, template_file_name),
        }
        files.append(from_templates)

    for template_file_name in template_file_names_1_x:

        # Handle files from 1.11.

        actual_file_name = Path(template_file_name).stem
        from_etc = {
            "source_file": "{0}/{1}".format(etc_dir, template_file_name),
            "target_file": "{0}/{1}".format(etc_dir, actual_file_name),
        }
        files.append(from_etc)

        # Handle files from 1.12 - 1.15.

        from_templates = {
            "source_file": "{0}/resources/templates/{1}".format(g2_dir, template_file_name),
            "target_file": "{0}/{1}".format(etc_dir, actual_file_name),
        }
        files.append(from_templates)

    # Copy files.

    for file in files:
        source_file = file.get("source_file")
        target_file = file.get("target_file")

        # Check if source file exists.

        if not os.path.exists(source_file):
            logging.debug(message_debug(902, target_file, source_file))
            continue

        # If source file exists and the target doesn't exist, copy.

        if not os.path.exists(target_file):
            logging.info(message_info(154, target_file, source_file))
            if not os.path.exists(os.path.dirname(target_file)):
                os.makedirs(os.path.dirname(target_file))
            shutil.copyfile(source_file, target_file)


def create_g2_lic(config):

    etc_dir = config.get("etc_dir")
    license_base64_encoded = config.get('license_base64_encoded')

    if license_base64_encoded:
        output_file_name = "{0}/g2.lic".format(etc_dir)
        logging.info(message_info(157, output_file_name))
        with open(output_file_name, "wb") as output_file:
            output_file.write(base64.b64decode(license_base64_encoded))

def create_server_keystore(config):

    etc_dir = config.get("etc_dir")
    api_server_key_store_base64_encoded = config.get('api_server_key_store_base64_encoded')

    if api_server_key_store_base64_encoded:
        output_file_name = "{0}/api-server-keystore.p12".format(etc_dir)
        logging.info(message_info(157, output_file_name))
        with open(output_file_name, "wb") as output_file:
            output_file.write(base64.b64decode(api_server_key_store_base64_encoded))

def create_client_keystore(config):

    etc_dir = config.get("etc_dir")
    api_server_client_key_store_base64_encoded = config.get('api_server_client_key_store_base64_encoded')

    if api_server_client_key_store_base64_encoded:
        output_file_name = "{0}/api-server-client-keystore.p12".format(etc_dir)
        logging.info(message_info(157, output_file_name))
        with open(output_file_name, "wb") as output_file:
            output_file.write(base64.b64decode(api_server_client_key_store_base64_encoded))


def create_g2config_gtc(config):

    etc_dir = config.get("etc_dir")
    filename = "{0}/G2Config.gtc".format(etc_dir)
    g2_config_gtc = config.get('g2_config_gtc')
    with open(filename, 'w') as output_file:
        if g2_config_gtc is not None:
            output_file.write(g2_config_gtc)
    logging.info(message_info(157, filename))


def delete_files(config):

    # Get paths.

    etc_dir = config.get("etc_dir")

    # Files to copy.

    files = [
        "{0}/g2config.json".format(etc_dir),
    ]

    # Copy files.

    for file in files:
        if os.path.exists(file):
            logging.info(message_info(155, file))
            os.remove(file)


def database_initialization_db2(config):
    logging.info(message_info(183))

    database_url = config.get('g2_database_url')
    parsed_database_url = parse_database_url(database_url)

    input_filename = "/opt/IBM/db2/clidriver/cfg/db2dsdriver.cfg.senzing-template"
    output_filename = "/opt/IBM/db2/clidriver/cfg/db2dsdriver.cfg"
    backup_filename = "{0}.{1}".format(output_filename, int(time.time()))

    # Detect error and exit, if needed.

    if not os.path.exists(input_filename):
        logging.warning(message_warning(510, input_filename))
        return

    # Backup existing file.

    if os.path.exists(output_filename):
        os.rename(output_filename, backup_filename)

    # Create new file from input_filename template. If engine_configuration_json is specified then
    # use engine_configuration_json to create db2dsdriver.cfg

    if config.get('engine_configuration_json'):
        db2dsdriver_contents = config.get('db2dsdriver_cfg_contents')
        if db2dsdriver_contents is None:
            exit_error(703)

        with open(output_filename, 'w') as out_file:
            out_file.write(db2dsdriver_contents)
    else:
        logging.info(message_info(160, output_filename, input_filename))
        with open(input_filename, 'r') as in_file:
            with open(output_filename, 'w') as out_file:
                for line in in_file:
                    out_file.write(line.format(**parsed_database_url))

    # Remove backup file if it is the same as the new file.

    if os.path.exists(backup_filename):
        if filecmp.cmp(output_filename, backup_filename):
            os.remove(backup_filename)
        else:
            logging.info(message_info(161, backup_filename, output_filename))

# The following method is just a docstring for use in creating a template file.


def database_initialization_mssql_odbc_ini_mssql_template():
    """[{schema}]
Database = G2
Description = Senzing MS SQL database for G2
Driver = ODBC Driver 17 for SQL Server
Server = {hostname},{port}
"""
    return 0


def database_initialization_mssql(config):
    logging.info(message_info(184))

    database_url = config.get('g2_database_url')
    parsed_database_url = parse_database_url(database_url)

    input_filename = "/etc/odbc.ini.mssql-template"
    output_filename = "/opt/microsoft/msodbcsql17/etc/odbc.ini"
    backup_filename = "{0}.{1}".format(output_filename, int(time.time()))

    # Detect error and exit, if needed.

    if not os.path.exists(input_filename):
        logging.warning(message_warning(510, input_filename))
        input_filename = "/tmp/odbc.ini.mssql-template"
        with open(input_filename, 'w') as in_file:
            logging.info(message_warning(157, input_filename))
            in_file.write(database_initialization_mssql_odbc_ini_mssql_template.__doc__)

    # Backup existing file.

    if os.path.exists(output_filename):
        os.rename(output_filename, backup_filename)

    # Create output directory.

    output_directory = os.path.dirname(output_filename)
    logging.info(message_info(162, output_directory))

    try:
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
    except PermissionError as err:
        exit_error(702, output_directory, err)

    # Create new file from input_filename template. If engine_configuration_json is specified then
    # use mssql_odbc_ini_contents to create osbc.ini

    if config.get('engine_configuration_json'):
        odbc_ini_contents = config.get('mssql_odbc_ini_contents')
        if odbc_ini_contents is None:
            exit_error(704)

        with open(output_filename, 'w') as out_file:
            out_file.write(odbc_ini_contents)
    else:
        logging.info(message_info(160, output_filename, input_filename))
        with open(input_filename, 'r') as in_file:
            with open(output_filename, 'w') as out_file:
                for line in in_file:
                    out_file.write(line.format(**parsed_database_url))

    # Remove backup file if it is the same as the new file.

    if os.path.exists(backup_filename):
        if filecmp.cmp(output_filename, backup_filename):
            os.remove(backup_filename)
        else:
            logging.info(message_info(161, backup_filename, output_filename))


def database_initialization_mysql(config):
    logging.info(message_info(185))

    database_url = config.get('g2_database_url')
    parsed_database_url = parse_database_url(database_url)

    url = "http://repo.mysql.com/apt/debian/pool/mysql-8.0/m/mysql-community/libmysqlclient21_8.0.20-1debian10_amd64.deb"
    filename = "/opt/senzing/g2/download/libmysqlclient.deb"
    libmysqlclient = "/opt/senzing/g2/lib/libmysqlclient.so.21.1.20"
    libmysqlclient_link = "/opt/senzing/g2/lib/libmysqlclient.so.21"

    # Download the file.

    if not os.path.exists(filename):
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        with urllib.request.urlopen(url) as response:
            with open(filename, 'wb') as out_file:
                logging.info(message_info(159, filename, url))
                shutil.copyfileobj(response, out_file)

    # Create file using "dpkg".

    if not os.path.exists(libmysqlclient):
        command = "dpkg --fsys-tarfile /opt/senzing/g2/download/libmysqlclient.deb | tar xOf - ./usr/lib/x86_64-linux-gnu/libmysqlclient.so.21.1.20  > {0}".format(libmysqlclient)
        os.environ["DEBIAN_FRONTEND"] = "noninteractive"
        logging.info(message_info(157, libmysqlclient))
        os.system(command)

    # Change file permissions.

    actual_file_permissions = os.stat(libmysqlclient).st_mode & 0o777
    requested_file_permissions = 0o755
    if actual_file_permissions != requested_file_permissions:
        logging.info(message_info(151, libmysqlclient, actual_file_permissions, requested_file_permissions))
        os.chmod(libmysqlclient, requested_file_permissions)

    # Make a soft link

    if not os.path.exists(libmysqlclient_link):
        libmysqlclient_filename = os.path.basename(libmysqlclient)
        logging.info(message_info(158, libmysqlclient_link, libmysqlclient))
        os.symlink(libmysqlclient_filename, libmysqlclient_link)


def database_initialization_postgresql(config):
    logging.info(message_info(186))

    # Install senzing postgresql governor if it is not installed.

    install_senzing_postgresql_governor(config)


def install_senzing_postgresql_governor(config):

    senzing_governor_path = "{0}/python/senzing_governor.py".format(config.get("g2_dir"))
    if not os.path.exists(senzing_governor_path):
        governor_url = config.get("governor_url")
        logging.info(message_info(180, senzing_governor_path, governor_url))
        try:
            urllib.request.urlretrieve(
                governor_url,
                senzing_governor_path)
        except urllib.error.URLError as err:
            logging.warning(message_warning(301, governor_url, err))
    else:
        logging.info(message_info(181, senzing_governor_path))


def database_initialization(config):
    ''' Given a canonical database URL, transform to the specific URL. '''

    result = ""

    enable_db2 = config.get('enable_db2')
    enable_mssql = config.get('enable_mssql')
    enable_mysql = config.get('enable_mysql')
    enable_postgresql = config.get('enable_postgresql')

    # Find default database scheme.

    database_url = config.get('g2_database_url')
    parsed_database_url = parse_database_url(database_url)
    scheme = parsed_database_url.get('scheme')
    database_urls = [database_url]

    # If engine_configuration_json given, find the scheme and make sure all of the schemes are the same.

    engine_configuration_json = config.get('engine_configuration_json')
    if engine_configuration_json:
        engine_configuration_dict = json.loads(engine_configuration_json)
        hybrid = engine_configuration_dict.get('HYBRID', {})
        database_keys = set(hybrid.values())

        # Create list of database URLs.

        database_urls = [engine_configuration_dict["SQL"]["CONNECTION"]]
        for database_key in database_keys:
            database_url = engine_configuration_dict.get(database_key, {}).get("DB_1", None)
            if database_url:
                database_urls.append(database_url)

        # Collect schemes from database URLs.

        schemes = []
        for database_url in database_urls:
            schemes.append(parse_database_url_scheme(database_url))

        # Delete duplicate schemes and make sure there is only one scheme used.

        schemes_set = set(schemes)
        if len(schemes_set) == 1:
            scheme = schemes[0]
        else:
            exit_error(801, schemes_set)

    # Format database URL for a particular database.

    if scheme in ['mysql'] or enable_mysql:
        result = database_initialization_mysql(config)
    elif scheme in ['postgresql'] or enable_postgresql:
        result = database_initialization_postgresql(config)
    elif scheme in ['db2'] or enable_db2:
        result = database_initialization_db2(config)
    elif scheme in ['sqlite3']:
        logging.info(message_info(182))
    elif scheme in ['mssql'] or enable_mssql:
        result = database_initialization_mssql(config)
    else:
        logging.error(message_error(695, scheme, database_url))

    return result

# -----------------------------------------------------------------------------
# Senzing services.
# -----------------------------------------------------------------------------


def get_g2_configuration_dictionary(config):
    ''' Construct a dictionary in the form of the old ini files. '''
    result = {
        "PIPELINE": {
            "CONFIGPATH": config.get("etc_dir"),
            "RESOURCEPATH": "{0}/resources".format(config.get("g2_dir")),
            "SUPPORTPATH": config.get("data_dir"),
        },
        "SQL": {
            "CONNECTION": config.get("g2_database_url_raw"),
        }
    }
    return result


def get_g2_configuration_json(config):
    ''' Return a JSON string with Senzing configuration. '''
    result = ""
    if config.get('engine_configuration_json'):
        result = config.get('engine_configuration_json')
    else:
        result = json.dumps(get_g2_configuration_dictionary(config))
    return result


def get_g2_config(config, g2_config_name="init-container-G2-config"):
    ''' Get the G2Config resource. '''
    global g2_config_singleton

    if g2_config_singleton:
        return g2_config_singleton

    try:
        g2_configuration_json = get_g2_configuration_json(config)
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


def do_debug_database_url(args):
    ''' For use with Docker acceptance testing. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)

    # Prolog.

    database_url = config.get('g2_database_url')
    parsed_database_url = parse_database_url(database_url)

    # Output

    print("")
    print("SENZING_DATABASE_URL={0}".format(database_url))
    print("")
    print("===== Results from parsing SENZING_DATABASE_URL =====")
    print("")
    print(json.dumps(parsed_database_url, sort_keys=True, indent=4))
    print("")

    input_filename = "/opt/IBM/db2/clidriver/cfg/db2dsdriver.cfg.senzing-template"

    # Detect error and exit, if needed.

    if os.path.exists(input_filename):

        print("===== Sample db2dsdriver.cfg =====")
        print("")

        if config.get('engine_configuration_json'):
            db2dsdriver_contents = config.get('db2dsdriver_cfg_contents')
            if db2dsdriver_contents is None:
                exit_error(703)
            print(db2dsdriver_contents)
        else:
            with open(input_filename, 'r') as in_file:
                for line in in_file:
                    print(line.format(**parsed_database_url).replace("\n", ""))


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

    # Sleep, if requested.

    delay(config)

    # Copy files.

    copy_files(config)

    # Change ini files

    change_module_ini(config)
    change_project_ini(config)

    # Database specific operations.

    database_initialization(config)

    # Manipulate files.

    change_directory_ownership(config)
    change_file_permissions(config)

    # If requested, create /etc/opt/senzing/g2.lic

    create_g2_lic(config)

    # If requested, create /etc/opt/senzing/api-server-keystore.p12

    create_server_keystore(config)

    # If requested, create /etc/opt/senzing/api-server-client-keystore.p12

    create_client_keystore(config)

    # If requested, create /etc/opt/senzing/G2Config.gtc

    create_g2config_gtc(config)

    # Get Senzing resources.

    g2_config = get_g2_config(config)
    g2_configuration_manager = get_g2_configuration_manager(config)

    # Initialize G2 database.

    g2_initializer = G2Initializer(g2_configuration_manager, g2_config)
    try:
        default_config_id = g2_initializer.create_default_config_id()
        if default_config_id:
            logging.info(message_info(170, default_config_id.decode()))
    except Exception as err:
        logging.error(message_error(701, err, type(err.__cause__), err.__cause__))

    # Cleanup.

    delete_files(config)

    # Epilog.

    logging.info(exit_template(config))


def do_initialize_database(args):
    ''' Do a task. '''

    # Get context from CLI, environment variables, and ini files.
    # A g2_database_url must be explicitly defined.

    configuration_locator['g2_database_url']['default'] = None
    config = get_configuration(args)

    # Prolog.

    logging.info(entry_template(config))

    # Update database configuration files.

    if config.get('g2_database_url'):
        database_initialization(config)
        if config.get('update_ini_files'):
            change_module_ini(config)
            change_project_ini(config)

    # Get Senzing resources.

    g2_config = get_g2_config(config)
    g2_configuration_manager = get_g2_configuration_manager(config)

    # Initialize G2 database.

    g2_initializer = G2Initializer(g2_configuration_manager, g2_config)
    try:
        default_config_id = g2_initializer.create_default_config_id()
        if default_config_id:
            logging.info(message_info(170, default_config_id.decode()))
    except Exception as err:
        logging.error(message_error(701, err, type(err.__cause__), err.__cause__))

    # Epilog.

    logging.info(exit_template(config))


def do_initialize_files(args):
    ''' Do a task. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)

    # Prolog.

    logging.info(entry_template(config))

    # Copy files.

    copy_files(config)

    # Change ini files

    change_module_ini(config)
    change_project_ini(config)

    # If requested, create /etc/opt/senzing/g2.lic

    create_g2_lic(config)

    # If requested, create /etc/opt/senzing/api-server-keystore.p12

    create_server_keystore(config)

    # If requested, create /etc/opt/senzing/api-server-client-keystore.p12

    create_client_keystore(config)

    # If requested, create /etc/opt/senzing/G2Config.gtc

    create_g2config_gtc(config)

    # Database specific operations.

    database_initialization(config)

    # Manipulate files.

    change_directory_ownership(config)
    change_file_permissions(config)

    # Cleanup.

    delete_files(config)

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

    # Sleep.

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
