# docker-init-container

If you are beginning your journey with [Senzing],
please start with [Senzing Quick Start guides].

You are in the [Senzing Garage] where projects are "tinkered" on.
Although this GitHub repository may help you understand an approach to using Senzing,
it's not considered to be "production ready" and is not considered to be part of the Senzing product.
Heck, it may not even be appropriate for your application of Senzing!

## Preamble

At [Senzing], we strive to create GitHub documentation in a
"[don't make me think]" style. For the most part, instructions are copy and paste.
Whenever thinking is needed, it's marked with a "thinking" icon :thinking:.
Whenever customization is needed, it's marked with a "pencil" icon :pencil2:.
If the instructions are not clear, please let us know by opening a new
[Documentation issue] describing where we can improve. Now on with the show...

## Overview

The `senzing/init-container` performs Senzing initializations.

**Synopsis:**

1. Where needed, copy `*.template` files into actual files.
1. Change file permissions and ownership of specific files.
1. Modify contents of specific `ini` files.
1. If needed, populate Senzing database `SYS_CFG` table with default configuration.
1. Initializations are performed by [init-container.py] script.

### Contents

1. [Expectations]
1. [Demonstrate using Command Line Interface]
   1. [Prerequisites for CLI]
   1. [Download]
   1. [Environment variables for CLI]
   1. [Run command]
1. [Demonstrate using Docker]
   1. [Prerequisites for Docker]
   1. [Database support]
   1. [External database]
   1. [Run Docker container]
1. [Configuration]
1. [References]

#### Legend

1. :thinking: - A "thinker" icon means that a little extra thinking may be required.
   Perhaps there are some choices to be made.
   Perhaps it's an optional step.
1. :pencil2: - A "pencil" icon means that the instructions may need modification before performing.
1. :warning: - A "warning" icon means that something tricky is happening, so pay attention.

## Expectations

- **Space:** This repository and demonstration require 6 GB free disk space.
- **Time:** Budget 40 minutes to get the demonstration up-and-running, depending on CPU and network speeds.
- **Background knowledge:** This repository assumes a working knowledge of:
  - [Docker]

## Demonstrate using Command Line Interface

### Prerequisites for CLI

:thinking: The following tasks need to be complete before proceeding.
These are "one-time tasks" which may already have been completed.

1. Install system dependencies:
   1. Use `apt` based installation for Debian, Ubuntu and
      [other Debian based]
      1. See [apt-packages.txt] for list
   1. Use `yum` based installation for Red Hat, CentOS, openSuse and
      [other RPM based].
      1. See [yum-packages.txt] for list
1. Install Python dependencies:
   1. See [requirements.txt] for list
      1. [Installation hints]
1. The following software programs need to be installed:
   1. [senzingapi]
1. :thinking: **Optional:** Some databases need additional support.
   For other databases, this step may be skipped.
   1. **Db2:** See
      [Support Db2].
   1. **MS SQL:** See
      [Support MS SQL].
1. [Configure Senzing database]

### Download

1. Get a local copy of
   [init-container.py].
   Example:

   1. :pencil2: Specify where to download file.
      Example:

      ```console
      export SENZING_DOWNLOAD_FILE=~/init-container.py
      ```

   1. Download file.
      Example:

      ```console
      curl -X GET \
        --output ${SENZING_DOWNLOAD_FILE} \
        https://raw.githubusercontent.com/Senzing/docker-init-container/main/init-container.py
      ```

   1. Make file executable.
      Example:

      ```console
      chmod +x ${SENZING_DOWNLOAD_FILE}
      ```

1. :thinking: **Alternative:** The entire git repository can be downloaded by following instructions at
   [Clone repository]

### Environment variables for CLI

1. :pencil2: Identify the Senzing `g2` directory.
   Example:

   ```console
   export SENZING_G2_DIR=/opt/senzing/g2
   ```

   1. Here's a simple test to see if `SENZING_G2_DIR` is correct.
      The following command should return file contents.
      Example:

      ```console
      cat ${SENZING_G2_DIR}/g2BuildVersion.json
      ```

1. Set common environment variables
   Example:

   ```console
   export PYTHONPATH=${SENZING_G2_DIR}/sdk/python
   ```

1. :thinking: Set operating system specific environment variables.
   Choose one of the options.

   1. **Option #1:** For Debian, Ubuntu, and [other Debian based].
      Example:

      ```console
      export LD_LIBRARY_PATH=${SENZING_G2_DIR}/lib:${SENZING_G2_DIR}/lib/debian:$LD_LIBRARY_PATH
      ```

   1. **Option #2** For Red Hat, CentOS, openSuse and [other RPM based].
      Example:

      ```console
      export LD_LIBRARY_PATH=${SENZING_G2_DIR}/lib:$LD_LIBRARY_PATH
      ```

### Run command

1. Run the command.
   Example:

   ```console
   sudo \
     PYTHONPATH=${PYTHONPATH} \
     LD_LIBRARY_PATH=${LD_LIBRARY_PATH} \
     ${SENZING_DOWNLOAD_FILE} --help
   ```

1. For more examples of use, see [Examples of CLI].

## Demonstrate using Docker

### Prerequisites for Docker

:thinking: The following tasks need to be complete before proceeding.
These are "one-time tasks" which may already have been completed.

1. The following software programs need to be installed:
   1. [Docker]
1. [Install Senzing using Docker]
1. [Configure Senzing database using Docker]

### Database support

:thinking: **Optional:** Some databases need additional support.
For other databases, these steps may be skipped.

1. **Db2:** See
   [Support Db2] instructions to set `SENZING_OPT_IBM_DIR_PARAMETER`.
1. **MS SQL:** See
   [Support MS SQL] instructions to set `SENZING_OPT_MICROSOFT_DIR_PARAMETER`.

### External database

:thinking: **Optional:** Use if storing data in an external database.
If not specified, the internal SQLite database will be used.

1. :pencil2: Specify database.
   Example:

   ```console
   export DATABASE_PROTOCOL=postgresql
   export DATABASE_USERNAME=postgres
   export DATABASE_PASSWORD=postgres
   export DATABASE_HOST=senzing-postgresql
   export DATABASE_PORT=5432
   export DATABASE_DATABASE=G2
   ```

1. Construct Database URL.
   Example:

   ```console
   export SENZING_DATABASE_URL="${DATABASE_PROTOCOL}://${DATABASE_USERNAME}:${DATABASE_PASSWORD}@${DATABASE_HOST}:${DATABASE_PORT}/${DATABASE_DATABASE}"
   ```

1. Construct parameter for `docker run`.
   Example:

   ```console
   export SENZING_DATABASE_URL_PARAMETER="--env SENZING_DATABASE_URL=${SENZING_DATABASE_URL}"
   ```

### Run Docker container

Although the `Docker run` command looks complex,
it accounts for all of the optional variations described above.
Unset environment variables have no effect on the
`docker run` command and may be removed or remain.

1. Run Docker container.
   Example:

   ```console
   sudo docker run \
     --rm \
     ${SENZING_DATABASE_URL_PARAMETER} \
     ${SENZING_OPT_IBM_DIR_PARAMETER} \
     ${SENZING_OPT_MICROSOFT_DIR_PARAMETER} \
     senzing/init-container
   ```

1. For more examples of use, see [Examples of Docker].

## Configuration

Configuration values specified by environment variable or command line parameter.

- **[SENZING_DATABASE_URL]**
- **[SENZING_DEBUG]**

## References

1. [Development](docs/development.md)
1. [Errors](docs/errors.md)
1. [Examples](docs/examples.md)
1. Related artifacts:
   1. [DockerHub](https://hub.docker.com/r/senzing/init-container)
   1. [Helm Chart](https://github.com/senzing-garage/charts/tree/main/charts/senzing-init-container)

[apt-packages.txt]: src/apt-packages.txt
[Clone repository]: docs/development.md#clone-repository
[Configuration]: #configuration
[Configure Senzing database using Docker]: https://github.com/senzing-garage/knowledge-base/blob/main/HOWTO/configure-senzing-database-using-docker.md
[Configure Senzing database]: https://github.com/senzing-garage/knowledge-base/blob/main/HOWTO/configure-senzing-database.md
[Database support]: #database-support
[Demonstrate using Command Line Interface]: #demonstrate-using-command-line-interface
[Demonstrate using Docker]: #demonstrate-using-docker
[Development]: docs/development.md
[Docker]: https://github.com/senzing-garage/knowledge-base/blob/main/WHATIS/docker.md
[DockerHub]: https://hub.docker.com/r/senzing/init-container
[Documentation issue]: https://github.com/senzing-garage/docker-init-container/issues/new?template=documentation_request.md
[don't make me think]: https://github.com/senzing-garage/knowledge-base/blob/main/WHATIS/dont-make-me-think.md
[Download]: #download
[Environment variables for CLI]: #environment-variables-for-cli
[Errors]: docs/errors.md
[Examples of CLI]: docs/examples.md#examples-of-cli
[Examples of Docker]: docs/examples.md#examples-of-docker
[Examples]: docs/examples.md
[Expectations]: #expectations
[External database]: #external-database
[Helm Chart]: https://github.com/senzing-garage/charts/tree/main/charts/senzing-init-container
[init-container.py]: init-container.py
[Install Senzing using Docker]: https://github.com/senzing-garage/knowledge-base/blob/main/HOWTO/install-senzing-using-docker.md
[Installation hints]: https://github.com/senzing-garage/knowledge-base/blob/main/HOWTO/install-python-dependencies.md
[other Debian based]: https://en.wikipedia.org/wiki/List_of_Linux_distributions#Debian-based
[other RPM based]: https://en.wikipedia.org/wiki/List_of_Linux_distributions#RPM-based
[Prerequisites for CLI]: #prerequisites-for-cli
[Prerequisites for Docker]: #prerequisites-for-docker
[References]: #references
[requirements.txt]: requirements.txt
[Run command]: #run-command
[Run Docker container]: #run-docker-container
[Senzing Garage]: https://github.com/senzing-garage
[Senzing Quick Start guides]: https://docs.senzing.com/quickstart/
[SENZING_DATABASE_URL]: https://github.com/senzing-garage/knowledge-base/blob/main/lists/environment-variables.md#senzing_database_url
[SENZING_DEBUG]: https://github.com/senzing-garage/knowledge-base/blob/main/lists/environment-variables.md#senzing_debug
[Senzing]: https://senzing.com/
[senzingapi]: https://github.com/senzing-garage/knowledge-base/blob/main/HOWTO/install-senzing-api.md
[Support Db2]: https://github.com/senzing-garage/knowledge-base/blob/main/HOWTO/support-db2.md
[Support Db2]: https://github.com/senzing-garage/knowledge-base/blob/main/HOWTO/support-db2.md
[Support MS SQL]: https://github.com/senzing-garage/knowledge-base/blob/main/HOWTO/support-mssql.md
[Support MS SQL]: https://github.com/senzing-garage/knowledge-base/blob/main/HOWTO/support-mssql.md
[yum-packages.txt]: src/yum-packages.txt
