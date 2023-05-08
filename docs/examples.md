# docker-init-container examples

## Examples of CLI

The following examples require initialization described in
[Demonstrate using Command Line Interface](#demonstrate-using-command-line-interface).

### Init a Senzing volume and PostgreSQL

In this example, the `/etc` and `/var` directories are initialized
**and** the database is initialized.

1. :pencil2: Specify `SENZING_VOLUME`.
   Example:

    ```console
    export SENZING_VOLUME=/opt/my-senzing
    ```

1. Change ownership of `SENZING_VOLUME`.
   Example:

    ```console
    sudo chown $(id -u):$(id -g) -R ${SENZING_VOLUME}
    ```

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

1. Run command.
   Example:

    ```console
    sudo \
      PYTHONPATH=${PYTHONPATH} \
      LD_LIBRARY_PATH=${LD_LIBRARY_PATH} \
      --preserve-env \
      init-container.py initialize \
        --database-url ${SENZING_DATABASE_URL} \
        --etc-dir  ${SENZING_VOLUME}/etc \
        --g2-dir   ${SENZING_VOLUME}/g2 \
        --data-dir ${SENZING_VOLUME}/data \
        --var-dir  ${SENZING_VOLUME}/var
    ```

### Init Senzing volume

In this example, the `/etc` and `/var` directories are initialized.
The database is not initialized.

1. :pencil2: Specify `SENZING_VOLUME`.
   Example:

    ```console
    export SENZING_VOLUME=/opt/my-senzing
    ```

1. Change ownership of `SENZING_VOLUME`.
   Example:

    ```console
    sudo chown $(id -u):$(id -g) -R ${SENZING_VOLUME}
    ```

1. Run command.
   Example:

    ```console
    sudo \
      PYTHONPATH=${PYTHONPATH} \
      LD_LIBRARY_PATH=${LD_LIBRARY_PATH} \
      --preserve-env \
      init-container.py initialize-files \
        --etc-dir  ${SENZING_VOLUME}/etc \
        --g2-dir   ${SENZING_VOLUME}/g2 \
        --data-dir ${SENZING_VOLUME}/data \
        --var-dir  ${SENZING_VOLUME}/var
    ```

### Init PostgreSQL

In this example, a PostgreSQL database is initialized.

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

1. Run command.
   Example:

    ```console
    sudo \
      PYTHONPATH=${PYTHONPATH} \
      LD_LIBRARY_PATH=${LD_LIBRARY_PATH} \
      --preserve-env \
      init-container.py initialize-database \
        --database-url ${SENZING_DATABASE_URL} \
        --etc-dir  ${SENZING_VOLUME}/etc \
        --g2-dir   ${SENZING_VOLUME}/g2 \
        --data-dir ${SENZING_VOLUME}/data \
        --var-dir  ${SENZING_VOLUME}/var
    ```

## Examples of Docker

The following examples require initialization described in
[Demonstrate using Docker](#demonstrate-using-docker).
