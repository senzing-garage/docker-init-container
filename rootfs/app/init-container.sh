#!/usr/bin/env bash
# Make changes to files based on Environment Variables.

VERSION=1.0.0

# Debugging. Values: 0 for no debugging; 1 for debugging.

DEBUG=${SENZING_DEBUG:-0}

# A file used to determine if/when this program has previously run.

SENTINEL_FILE=${SENZING_ROOT}/init-container.sentinel

# Return codes.

OK=0
NOT_OK=1

# Location of this shell script.

SCRIPT_DIRECTORY=$(dirname ${0})

# Short-circuit for certain commandline options.

if [ "$1" == "--version" ]; then
  echo "init-container.sh version ${VERSION}"
  exit ${OK}
fi

# Exit if one-time initialization has been previously performed.

if [ -f ${SENTINEL_FILE} ]; then
  if [ ${DEBUG} -gt 0 ]; then
    echo "Sentinel file ${SENTINEL_FILE} exist. Initialization has already been done."
  fi
  exit ${OK}
fi

# Verify environment variables.

if [ -z "${SENZING_ROOT}" ]; then
  echo "ERROR: Environment variable SENZING_ROOT not set."
  exit ${NOT_OK}
fi

# Parse the SENZING_DATABASE_URL.

PARSED_SENZING_DATABASE_URL=$(${SCRIPT_DIRECTORY}/parse_senzing_database_url.py)
PROTOCOL=$(echo ${PARSED_SENZING_DATABASE_URL} | jq --raw-output '.scheme')
NETLOC=$(echo ${PARSED_SENZING_DATABASE_URL} | jq --raw-output '.netloc')
USERNAME=$(echo ${PARSED_SENZING_DATABASE_URL} | jq --raw-output  '.username')
PASSWORD=$(echo ${PARSED_SENZING_DATABASE_URL} | jq --raw-output  '.password')
HOST=$(echo ${PARSED_SENZING_DATABASE_URL} | jq --raw-output  '.hostname')
PORT=$(echo ${PARSED_SENZING_DATABASE_URL} | jq --raw-output  '.port')
DB_PATH=$(echo ${PARSED_SENZING_DATABASE_URL} | jq --raw-output  '.path')
SCHEMA=$(echo ${PARSED_SENZING_DATABASE_URL} | jq --raw-output  '.schema')

if [ ${DEBUG} -gt 0 ]; then
  echo "PROTOCOL: ${PROTOCOL}"
  echo "  NETLOC: ${NETLOC}"
  echo "USERNAME: ${USERNAME}"
  echo "PASSWORD: ${PASSWORD}"
  echo "    HOST: ${HOST}"
  echo "    PORT: ${PORT}"
  echo "    PATH: ${DB_PATH}"
  echo "  SCHEMA: ${SCHEMA}"
fi

# Set NEW_SENZING_DATABASE_URL.

NEW_SENZING_DATABASE_URL=""
if [ "${PROTOCOL}" == "sqlite3" ]; then
  NEW_SENZING_DATABASE_URL="${PROTOCOL}://${NETLOC}${DB_PATH}"
elif [ "${PROTOCOL}" == "mysql" ]; then
  NEW_SENZING_DATABASE_URL="${PROTOCOL}://${USERNAME}:${PASSWORD}@${HOST}:${PORT}/?schema=${SCHEMA}"
elif [ "${PROTOCOL}" == "postgresql" ]; then
  NEW_SENZING_DATABASE_URL="${PROTOCOL}://${USERNAME}:${PASSWORD}@${HOST}:${PORT}:${SCHEMA}/"
elif [ "${PROTOCOL}" == "db2" ]; then
  NEW_SENZING_DATABASE_URL="${PROTOCOL}://${USERNAME}:${PASSWORD}@${SCHEMA}"
else
  echo "ERROR: Unknown protocol: ${PROTOCOL}"
  exit ${NOT_OK}
fi

if [ ${DEBUG} -gt 0 ]; then
  echo "NEW_SENZING_DATABASE_URL: ${NEW_SENZING_DATABASE_URL}"
fi

# -----------------------------------------------------------------------------
# Handle "sqlite3" protocol.
# -----------------------------------------------------------------------------

if [ "${PROTOCOL}" == "sqlite3" ]; then

  true  # Need a statement in bash if/else

# -----------------------------------------------------------------------------
# Handle "mysql" protocol.
# -----------------------------------------------------------------------------

elif [ "${PROTOCOL}" == "mysql" ]; then

  # Make temporary directory in SENZING_ROOT.

  mkdir -p ${SENZING_ROOT}/tmp

  # Prevent interactivity.

  export DEBIAN_FRONTEND=noninteractive

  # Install libmysqlclient21.

  wget \
    --output-document=${SENZING_ROOT}/tmp/libmysqlclient.deb \
    http://repo.mysql.com/apt/debian/pool/mysql-8.0/m/mysql-community/libmysqlclient21_8.0.16-2debian9_amd64.deb

  dpkg --fsys-tarfile ${SENZING_ROOT}/tmp/libmysqlclient.deb \
    | tar xOf - ./usr/lib/x86_64-linux-gnu/libmysqlclient.so.21.0.16 \
    > ${SENZING_ROOT}/g2/lib/libmysqlclient.so.21.0.16

  ln -s ${SENZING_ROOT}/g2/lib/libmysqlclient.so.21.0.16 ${SENZING_ROOT}/g2/lib/libmysqlclient.so.21

# -----------------------------------------------------------------------------
# Handle "postgresql" protocol.
# -----------------------------------------------------------------------------

elif [ "${PROTOCOL}" == "postgresql" ]; then

  true  # Need a statement in bash if/else

# -----------------------------------------------------------------------------
# Handle "db2" protocol.
# -----------------------------------------------------------------------------

elif [ "${PROTOCOL}" == "db2" ]; then

  mv ${SENZING_ROOT}/db2/clidriver/cfg/db2dsdriver.cfg ${SENZING_ROOT}/db2/clidriver/cfg/db2dsdriver.cfg.original
  cp /opt/IBM/db2/clidriver/cfg/db2dsdriver.cfg.db2-template ${SENZING_ROOT}/db2/clidriver/cfg/db2dsdriver.cfg
  sed -i.$(date +%s) \
    -e "s/{HOST}/${HOST}/g" \
    -e "s/{PORT}/${PORT}/g" \
    -e "s/{SCHEMA}/${SCHEMA}/g" \
    ${SENZING_ROOT}/db2/clidriver/cfg/db2dsdriver.cfg

  if [ ${DEBUG} -gt 0 ]; then
    echo "---------- ${SENZING_ROOT}/db2/clidriver/cfg/db2dsdriver.cfg -------------------------"
    cat ${SENZING_ROOT}/db2/clidriver/cfg/db2dsdriver.cfg
  fi

fi

# -----------------------------------------------------------------------------
# Handle common changes.
# -----------------------------------------------------------------------------

# G2Project.ini

sed -i.$(date +%s) \
  -e "s|G2Connection=sqlite3://na:na@${SENZING_ROOT}/g2/sqldb/G2C.db|G2Connection=${NEW_SENZING_DATABASE_URL}|g" \
  ${SENZING_ROOT}/g2/python/G2Project.ini

if [ ${DEBUG} -gt 0 ]; then
  echo "---------- g2/python/G2Project.ini --------------------------------------------"
  cat ${SENZING_ROOT}/g2/python/G2Project.ini
fi

# G2Module.ini

sed -i.$(date +%s) \
  -e "s|CONNECTION=sqlite3://na:na@${SENZING_ROOT}/g2/sqldb/G2C.db|CONNECTION=${NEW_SENZING_DATABASE_URL}|g" \
  ${SENZING_ROOT}/g2/python/G2Module.ini

if [ ${DEBUG} -gt 0 ]; then
  echo "---------- g2/python/G2Module.ini ---------------------------------------------"
  cat ${SENZING_ROOT}/g2/python/G2Module.ini
  echo "-------------------------------------------------------------------------------"
fi

# -----------------------------------------------------------------------------
# Epilog
# -----------------------------------------------------------------------------

# Append to a "sentinel file" to indicate when this script has been run.
# The sentinel file is used to identify the first run from subsequent runs for "first-time" processing.

echo "$(date) ${PROTOCOL}" >> ${SENTINEL_FILE}
