ARG BASE_IMAGE=debian:11.2-slim@sha256:4c25ffa6ef572cf0d57da8c634769a08ae94529f7de5be5587ec8ce7b9b50f9c
FROM ${BASE_IMAGE}

ENV REFRESHED_AT=2022-02-08

LABEL Name="senzing/init-container" \
      Maintainer="support@senzing.com" \
      Version="1.7.2"

HEALTHCHECK CMD ["/app/healthcheck.sh"]

# Run as "root" for system installation.

USER root

RUN apt update \
 && apt -y install \
      libaio1 \
      odbc-postgresql \
      python3 \
&& rm -rf /var/lib/apt/lists/*

# Copy files from repository.

COPY ./rootfs /
COPY init-container.py /app

# Make non-root container.

USER 1001:1001

# Set enviroment variables.

ENV SENZING_SUBCOMMAND=initialize

# Runtime execution.

WORKDIR /app
ENTRYPOINT ["/app/init-container.py"]
