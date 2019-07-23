#! /usr/bin/env python3

# -----------------------------------------------------------------------------
# g2-configuration-initializer.py
# -----------------------------------------------------------------------------

from glob import glob
import argparse
import json
import linecache
import logging
import os
import signal
import string
import sys
import time
from urllib.parse import urlparse, urlunparse

try:
    from G2Config import G2Config
    from G2ConfigMgr import G2ConfigMgr
    import G2Exception
except ImportError:
    pass

__all__ = []
__version__ = "1.0.0"
__date__ = '2019-07-16'
__updated__ = '2019-07-23'

SENZING_PRODUCT_ID = "5005"  # See https://github.com/Senzing/knowledge-base/blob/master/lists/senzing-product-ids.md
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
        "default": "/opt/senzing/g2/data",
        "env": "SENZING_CONFIG_PATH",
        "cli": "config-path"
    },
    "debug": {
        "default": False,
        "env": "SENZING_DEBUG",
        "cli": "debug"
    },
    "g2_database_url_generic": {
        "default": "sqlite3://na:na@/opt/senzing/g2/sqldb/G2C.db",
        "env": "SENZING_DATABASE_URL",
        "cli": "database-url"
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
        "default": "/opt/senzing/g2/data",
        "env": "SENZING_SUPPORT_PATH",
        "cli": "support-path"
    }
}

# Enumerate keys in 'configuration_locator' that should not be printed to the log.

keys_to_redact = [
    "g2_database_url_generic",
    "g2_database_url_specific"
    ]

# -----------------------------------------------------------------------------
# Define argument parser
# -----------------------------------------------------------------------------


def get_parser():
    ''' Parse commandline arguments. '''

    parser = argparse.ArgumentParser(prog="g2-configuration-initializer.py", description="Initialized Senzing's G2 Database with JSON")
    subparsers = parser.add_subparsers(dest='subcommand', help='Subcommands (SENZING_SUBCOMMAND):')

    subparser_1 = subparsers.add_parser('initialize', help='Create initial configuration in G2 database.')
    subparser_1.add_argument("--config-path", dest="config_path", metavar="SENZING_CONFIG_PATH", help="Location of Senzing's configuration template. Default: /opt/senzing/g2/data")
    subparser_1.add_argument("--database-url", dest="g2_database_url_generic", metavar="SENZING_DATABASE_URL", help="Information for connecting to database.")
    subparser_1.add_argument("--debug", dest="debug", action="store_true", help="Enable debugging. (SENZING_DEBUG) Default: False")
    subparser_1.add_argument("--support-path", dest="support_path", metavar="SENZING_SUPPORT_PATH", help="Location of Senzing's support. Default: /opt/senzing/g2/data")

    subparser_2 = subparsers.add_parser('list-configurations', help='List configurations.')
    subparser_2.add_argument("--config-path", dest="config_path", metavar="SENZING_CONFIG_PATH", help="Location of Senzing's configuration template. Default: /opt/senzing/g2/data")
    subparser_2.add_argument("--database-url", dest="g2_database_url_generic", metavar="SENZING_DATABASE_URL", help="Information for connecting to database.")
    subparser_2.add_argument("--debug", dest="debug", action="store_true", help="Enable debugging. (SENZING_DEBUG) Default: False")
    subparser_2.add_argument("--support-path", dest="support_path", metavar="SENZING_SUPPORT_PATH", help="Location of Senzing's support. Default: /opt/senzing/g2/data")

    subparser_3 = subparsers.add_parser('list-datasources', help='List datasources.')
    subparser_3.add_argument("--config-path", dest="config_path", metavar="SENZING_CONFIG_PATH", help="Location of Senzing's configuration template. Default: /opt/senzing/g2/data")
    subparser_3.add_argument("--database-url", dest="g2_database_url_generic", metavar="SENZING_DATABASE_URL", help="Information for connecting to database.")
    subparser_3.add_argument("--debug", dest="debug", action="store_true", help="Enable debugging. (SENZING_DEBUG) Default: False")
    subparser_3.add_argument("--support-path", dest="support_path", metavar="SENZING_SUPPORT_PATH", help="Location of Senzing's support. Default: /opt/senzing/g2/data")

    subparser_4 = subparsers.add_parser('wait-for-database', help='Wait until database is active.')
    subparser_4.add_argument("--database-url", dest="g2_database_url_generic", metavar="SENZING_DATABASE_URL", help="Information for connecting to database.")
    subparser_4.add_argument("--debug", dest="debug", action="store_true", help="Enable debugging. (SENZING_DEBUG) Default: False")

    subparser_8 = subparsers.add_parser('sleep', help='Do nothing but sleep. For Docker testing.')
    subparser_8.add_argument("--sleep-time-in-seconds", dest="sleep_time_in_seconds", metavar="SENZING_SLEEP_TIME_IN_SECONDS", help="Sleep time in seconds. DEFAULT: 0 (infinite)")

    subparser_9 = subparsers.add_parser('version', help='Print version of stream-loader.py.')
    subparser_10 = subparsers.add_parser('docker-acceptance-test', help='For Docker acceptance testing.')

    return parser

# -----------------------------------------------------------------------------
# Message handling
# -----------------------------------------------------------------------------

# 1xx Informational (i.e. logging.info())
# 3xx Warning (i.e. logging.warning())
# 5xx User configuration issues (either logging.warning() or logging.err() for Client errors)
# 7xx Internal error (i.e. logging.error for Server errors)
# 9xx Debugging (i.e. logging.debug())


message_dictionary = {
    "100": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}I",
    "101": "Enter {0}",
    "102": "Exit {0}",
    "103": "Sleeping {0} seconds.",
    "104": "Sleeping infinitely.",
    "105": "Waiting for database connection to {0}. Sleeping {1} seconds.",
    "110": "Default configuration already exists. SYS_CFG.CONFIG_DATA_ID = {0}. No modification needed.",
    "111": "New configuration created. SYS_CFG.CONFIG_DATA_ID = {0}",
    "112": "Configurations: {0}",
    "113": "Datasources: {0}",
    "197": "Version: {0}  Updated: {1}",
    "198": "For information on warnings and errors, see https://github.com/Senzing/stream-loader#errors",
    "199": "{0}",
    "300": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}W",
    "500": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "501": "Unknown database scheme '{0}' in database url '{1}'",
    "598": "Bad SENZING_SUBCOMMAND: {0}.",
    "599": "No processing done.",
    "700": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "701": "Could not initialize G2Engine with '{0}'. Error: {1}",
    "702": "Could not initialize G2Config with '{0}'. Error: {1}",
    "703": "Could not initialize G2ConfigMgr with '{0}'. Error: {1}",
    "704": "Could not initialize G2Audit with '{0}'. Error: {1}",
    "705": "Could not initialize G2Diagnostic with '{0}'. Error: {1}",
    "706": "Could not initialize G2Hasher with '{0}'. Error: {1}",
    "707": "Could not initialize G2Product with '{0}'. Error: {1}",
    "720": "Original and new database URLs do not match. Original URL: {0}; Reconstructed URL: {1}",
    "750": "{1}({2}) TranslateG2ModuleException: {0}",
    "751": "{1}({2}) G2ModuleNotInitialized: {0}",
    "752": "{1}({2}) Exception: {0}",
    "753": "{0}({1}) exception",
    "754": "{1}({2}) Bad return code: {0}",
    "799": "Program terminated with error.",
    "900": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}D",
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
    return message_generic(100, index, *args)


def message_warning(index, *args):
    return message_generic(300, index, *args)


def message_error(index, *args):
    return message_generic(700, index, *args)


def message_debug(index, *args):
    return message_generic(900, index, *args)


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

    # Special case:  Tailored database URL

    result['g2_database_url_specific'] = get_g2_database_url_specific(result.get("g2_database_url_generic"))
    result['g2_database_url_generic_redacted'] = get_g2_database_url_redacted(result.get("g2_database_url_generic"))
    result['g2_database_url_specific_redacted'] = get_g2_database_url_redacted(result.get("g2_database_url_generic"))

    return result


def validate_configuration(config):
    ''' Check aggregate configuration from commandline options, environment variables, config files, and defaults. '''

    user_warning_messages = []
    user_error_messages = []

    # Perform subcommand specific checking.

    subcommand = config.get('subcommand')

    if subcommand in ['initialize']:

        if not config.get('g2_database_url_generic'):
            user_error_messages.append(message_error(414))

    # Log warning messages.

    for user_warning_message in user_warning_messages:
        logging.warning(user_warning_message)

    # Log error messages.

    for user_error_message in user_error_messages:
        logging.error(user_error_message)

    # Log where to go for help.

    if len(user_warning_messages) > 0 or len(user_error_messages) > 0:
        logging.info(message_info(198))

    # If there are error messages, exit.

    if len(user_error_messages) > 0:
        exit_error(599)


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
        logging.info(message_info(102, args))
        sys.exit(0)

    return result_function


def bootstrap_signal_handler(signal, frame):
    sys.exit(0)


def entry_template(config):
    ''' Format of entry message. '''
    debug = config.get("debug", False)
    config['start_time'] = time.time()
    final_config = redact_configuration(config)
    config_json = json.dumps(final_config, sort_keys=True)
    return message_info(101, config_json)


def exit_template(config):
    ''' Format of exit message. '''
    debug = config.get("debug", False)
    stop_time = time.time()
    config['stop_time'] = stop_time
    config['elapsed_time'] = stop_time - config.get('start_time', stop_time)
    final_config = redact_configuration(config)
    config_json = json.dumps(final_config, sort_keys=True)
    return message_info(102, config_json)


def exit_error(index, *args):
    ''' Log error message and exit program. '''
    logging.error(message_error(index, *args))
    logging.error(message_error(599))
    sys.exit(1)


def exit_silently():
    ''' Exit program. '''
    sys.exit(1)

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

    result = {}

    # Get the value of SENZING_DATABASE_URL environment variable.

    senzing_database_url = original_senzing_database_url

    # Create lists of safe and unsafe characters.

    unsafe_characters = get_unsafe_characters(senzing_database_url)
    safe_characters = get_safe_characters(senzing_database_url)

    # Detect an error condition where there are not enough safe characters.

    if len(unsafe_characters) > len(safe_characters):
        logging.error(message_error(703, unsafe_characters, safe_characters))
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
        logging.warning(message_warning(720, original_senzing_database_url, test_senzing_database_url))

    # Return result.

    return result


def get_g2_database_url_specific(generic_database_url):
    result = ""

    parsed_database_url = parse_database_url(generic_database_url)
    scheme = parsed_database_url.get('scheme')

    if scheme in ['mysql']:
        result = "{scheme}://{username}:{password}@{hostname}:{port}/?schema={schema}".format(**parsed_database_url)
    elif scheme in ['postgresql']:
        result = "{scheme}://{username}:{password}@{hostname}:{port}:{schema}/".format(**parsed_database_url)
    elif scheme in ['db2']:
        result = "{scheme}://{username}:{password}@{schema}".format(**parsed_database_url)
    elif scheme in ['sqlite3']:
        result = "{scheme}://{netloc}{path}".format(**parsed_database_url)
    else:
        logging.error(message_error(501, scheme, generic_database_url))

    return result


def get_g2_database_url_redacted(generic_database_url):
    result = ""

    parsed_database_url = parse_database_url(generic_database_url)
    scheme = parsed_database_url.get('scheme')

    if scheme in ['mysql']:
        result = "{scheme}://xxxxxxxx:xxxxxxxx@{hostname}:{port}/?schema={schema}".format(**parsed_database_url)
    elif scheme in ['postgresql']:
        result = "{scheme}://xxxxxxxx:xxxxxxxx@{hostname}:{port}:{schema}/".format(**parsed_database_url)
    elif scheme in ['db2']:
        result = "{scheme}://xxxxxxxx:xxxxxxxx@{schema}".format(**parsed_database_url)
    elif scheme in ['sqlite3']:
        result = "{scheme}://xxxxxxxx:xxxxxxxx@{path}".format(**parsed_database_url)
    else:
        logging.error(message_error(501, scheme, generic_database_url))

    return result

# -----------------------------------------------------------------------------
# Get Senzing resources.
# -----------------------------------------------------------------------------


def get_g2_configuration_dictionary(config):
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
    return json.dumps(get_g2_configuration_dictionary(config))


def get_g2_config(config, g2_config_name="configuration-initializer-G2-config"):
    '''Get the G2Config resource.'''
    try:
        g2_configuration_json = get_g2_configuration_json(config)
        result = G2Config()
        result.initV2(g2_config_name, g2_configuration_json, config.get('debug', False))
    except G2Exception.G2ModuleException as err:
        exit_error(702, g2_configuration_json, err)
    return result


def get_g2_configuration_manager(config, g2_configuration_manager_name="configuration-initializer-G2-configuration-manager"):
    '''Get the G2Config resource.'''
    try:
        g2_configuration_json = get_g2_configuration_json(config)
        result = G2ConfigMgr()
        result.initV2(g2_configuration_manager_name, g2_configuration_json, config.get('debug', False))
    except G2Exception.G2ModuleException as err:
        exit_error(703, g2_configuration_json, err)
    return result

# -----------------------------------------------------------------------------
# do_* functions
#   Common function signature: do_XXX(args)
# -----------------------------------------------------------------------------


def do_docker_acceptance_test(args):
    ''' For use with Docker acceptance testing. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)
    validate_configuration(config)

    # Prolog.

    logging.info(entry_template(config))

    # Epilog.

    logging.info(exit_template(config))


def do_initialize(args):
    ''' Do a task. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)
    validate_configuration(config)

    # Prolog.

    logging.info(entry_template(config))

    # Determine of a default/initial G2 configuration already exists.

    default_config_id = bytearray()
    g2_configuration_manager = get_g2_configuration_manager(config)
    method = "g2_configuration_manager.getDefaultConfigID"
    parameters = default_config_id.decode()
    try:
        return_code = g2_configuration_manager.getDefaultConfigID(default_config_id)
    except G2Exception.TranslateG2ModuleException as err:
        logging.error(message_error(750, err, method, parameters))
    except G2Exception.G2ModuleNotInitialized as err:
        logging.error(message_error(751, err, method, parameters))
    except Exception as err:
        logging.error(message_error(752, err, method, parameters))
    except:
        logging.error(message_error(753, method, parameters))
    if return_code != 0:
        exit_error(754, return_code, method, parameters)

    # If a default configuration exists, there is nothing more to do.

    if default_config_id:
        logging.info(message_info(110, default_config_id.decode()))
        logging.info(exit_template(config))
        return

    # If there is no default configuration, create one in the 'configuration_bytearray' variable.

    g2_config = get_g2_config(config)
    config_handle = g2_config.create()
    configuration_bytearray = bytearray()
    method = "g2_config.save"
    parameters = "{0}, {1}".format(config_handle, configuration_bytearray.decode())
    try:
        return_code = g2_config.save(config_handle, configuration_bytearray)
    except G2Exception.TranslateG2ModuleException as err:
        logging.error(message_error(750, err, method, parameters))
    except G2Exception.G2ModuleNotInitialized as err:
        logging.error(message_error(751, err, method, parameters))
    except Exception as err:
        logging.error(message_error(752, err, method, parameters))
    except:
        logging.error(message_error(753, method, parameters))
    if return_code != 0:
        exit_error(754, return_code, method, parameters)

    g2_config.close(config_handle)

    # Save configuration JSON into G2 database.

    config_comment = "Initial configuration."
    new_config_id = bytearray()
    method = "g2_configuration_manager.addConfig"
    parameters = "{0}, {1}, {2}".format(configuration_bytearray.decode(), config_comment, new_config_id)
    try:
        return_code = g2_configuration_manager.addConfig(configuration_bytearray.decode(), config_comment, new_config_id)
    except G2Exception.TranslateG2ModuleException as err:
        logging.error(message_error(750, err, method, parameters))
    except G2Exception.G2ModuleNotInitialized as err:
        logging.error(message_error(751, err, method, parameters))
    except Exception as err:
        logging.error(message_error(752, err, method, parameters))
    except:
        logging.error(message_error(753, method, parameters))
    if return_code != 0:
        exit_error(754, return_code, method, parameters)

    # Set the default configuration ID.

    method = "g2_configuration_manager.setDefaultConfigID"
    parameters = "{0}".format(new_config_id)
    try:
        return_code = g2_configuration_manager.setDefaultConfigID(new_config_id)
    except G2Exception.TranslateG2ModuleException as err:
        logging.error(message_error(750, err, method, parameters))
    except G2Exception.G2ModuleNotInitialized as err:
        logging.error(message_error(751, err, method, parameters))
    except Exception as err:
        logging.error(message_error(752, err, method, parameters))
    except:
        logging.error(message_error(753, method, parameters))
    if return_code != 0:
        exit_error(754, return_code, method, parameters)

    # Epilog.

    logging.info(message_info(111, new_config_id.decode()))
    logging.info(exit_template(config))


def do_list_configurations(args):
    ''' List datasources in G2 database. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)
    validate_configuration(config)

    # Prolog.

    logging.info(entry_template(config))

    # Get list of configurations.

    list_bytearray = bytearray()
    g2_configuration_manager = get_g2_configuration_manager(config)
    method = "g2_configuration_manager.getConfigList"
    parameters = list_bytearray.decode()
    try:
        return_code = g2_configuration_manager.getConfigList(list_bytearray)
    except G2Exception.TranslateG2ModuleException as err:
        logging.error(message_error(750, err, method, parameters))
    except G2Exception.G2ModuleNotInitialized as err:
        logging.error(message_error(751, err, method, parameters))
    except Exception as err:
        logging.error(message_error(752, err, method, parameters))
    except:
        logging.error(message_error(753, method, parameters))
    if return_code != 0:
        exit_error(754, return_code, method, parameters)

    # Epilog.

    logging.info(message_info(112, list_bytearray.decode()))
    logging.info(exit_template(config))


def do_list_datasources(args):
    ''' List configurations in G2 database. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)
    validate_configuration(config)

    # Prolog.

    logging.info(entry_template(config))

    # Get list of configurations.

    g2_config = get_g2_config(config)
    config_handle = g2_config.create()
    datasources_bytearray = bytearray()
    method = "g2_config.listDataSources"
    parameters = "{0}, {1}".format(config_handle, datasources_bytearray.decode())
    try:
        return_code = g2_config.listDataSources(config_handle, datasources_bytearray)
    except G2Exception.TranslateG2ModuleException as err:
        logging.error(message_error(750, err, method, parameters))
    except G2Exception.G2ModuleNotInitialized as err:
        logging.error(message_error(751, err, method, parameters))
    except Exception as err:
        logging.error(message_error(752, err, method, parameters))
    except:
        logging.error(message_error(753, method, parameters))
    if return_code != 0:
        exit_error(754, return_code, method, parameters)

    # Epilog.

    logging.info(message_info(113, datasources_bytearray.decode()))
    logging.info(exit_template(config))


def do_sleep(args):
    ''' Sleep.  Used for debugging. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)
    validate_configuration(config)

    # Prolog.

    logging.info(entry_template(config))

    # Pull values from configuration.

    sleep_time_in_seconds = config.get('sleep_time_in_seconds')

    # Sleep

    if sleep_time_in_seconds > 0:
        logging.info(message_info(103, sleep_time_in_seconds))
        time.sleep(sleep_time_in_seconds)

    else:
        sleep_time_in_seconds = 3600
        while True:
            logging.info(message_info(104))
            time.sleep(sleep_time_in_seconds)

    # Epilog.

    logging.info(exit_template(config))


def do_version(args):
    ''' Log version information. '''

    logging.info(message_info(197, __version__, __updated__))


def do_wait_for_database(args):
    ''' Return after database connection is established. '''

    # Get context from CLI, environment variables, and ini files.

    config = get_configuration(args)
    validate_configuration(config)

    # Prolog.

    logging.info(entry_template(config))

    # Pull values from configuration.

    sleep_time_in_seconds = config.get('sleep_time_in_seconds')
    g2_database_url_specific_redacted = config.get('g2_database_url_specific_redacted')

    # Adjust sleep time if "0" default.

    if sleep_time_in_seconds <= 0:
        sleep_time_in_seconds = 15

    # See if G2 can access the database.

    g2_configuration_manager_name = "configuration-initializer-G2-configuration-manager"
    g2_configuration_json = get_g2_configuration_json(config)
    not_connected = True
    while not_connected:
        try:
            g2_configuration_manager = G2ConfigMgr()
            g2_configuration_manager.initV2(g2_configuration_manager_name, g2_configuration_json, config.get('debug', False))
        except Exception as err:
            not_connected = True
            g2_configuration_manager.destroy()
            logging.info(message_info(105, g2_database_url_specific_redacted, sleep_time_in_seconds))
            time.sleep(sleep_time_in_seconds)

    # Epilog.

    logging.info(exit_template(config))

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
        logging.warning(message_warning(598, subcommand))
        parser.print_help()
        exit_silently()

    # Tricky code for calling function based on string.

    globals()[subcommand_function_name](args)
