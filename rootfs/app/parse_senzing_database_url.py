#! /usr/bin/env python

import json
import os
import string
import sys

try:
    from urllib.parse import urlparse, urlunparse
except:
    from urlparse import urlparse, urlunparse

# Lists from https://www.ietf.org/rfc/rfc1738.txt

safe_character_list = ['$', '-', '_', '.', '+', '!', '*', '(', ')', ',', '"' ] + list(string.ascii_letters)
unsafe_character_list = [ '"', '<', '>', '#', '%', '{', '}', '|', '\\', '^', '~', '[', ']', '`']
reserved_character_list = [ ';', ',', '/', '?', ':', '@', '=', '&']


def translate(map, astring):
    new_string = str(astring)
    for key, value in list(map.items()):
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

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


if __name__ == "__main__":

    result = {
        'scheme': "",
        'netloc': "",
        'path': "",
        'params': "",
        'query': "",
        'fragment': "",
        'username': "",
        'password': "",
        'hostname': "",
        'port': "",
        'schema': "",
    }

    # Get the value of SENZING_DATABASE_URL environment variable.

    original_senzing_database_url = os.environ.get('SENZING_DATABASE_URL', "sqlite3://na:na@/opt/senzing/g2/sqldb/G2C.db")
    result.update({
        "originalUrl": original_senzing_database_url
    })
    senzing_database_url = original_senzing_database_url

    # Create lists of safe and unsafe characters.

    unsafe_characters = get_unsafe_characters(senzing_database_url)
    safe_characters = get_safe_characters(senzing_database_url)

    # Detect an error condition where there are not enough safe characters.

    if len(unsafe_characters) > len(safe_characters):
        result.update({
            "error": "There are not enough safe characters to do the translation.",
            "unsafeCharacters": unsafe_characters,
            "safeCharacters": safe_characters,
        })
        result_json = json.dumps(result)
        print(result_json)
        sys.exit(1)

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
        result.update({
            "error": "Original and new URLs do not match.",
            "originalUrl": original_senzing_database_url,
            "newUrl": test_senzing_database_url,
        })

    # Print successful results.

    result_json = json.dumps(result)
    print(result_json)
