ARG BASE_IMAGE=senzing/senzing-base:1.1.0
FROM ${BASE_IMAGE}

ENV REFRESHED_AT=2019-08-05

LABEL Name="senzing/init-container" \
      Maintainer="support@senzing.com" \
      Version="1.3.0"

HEALTHCHECK CMD ["/app/healthcheck.sh"]

# Run as "root" for system installation.

USER root

# Copy files from repository.

COPY ./rootfs /

# Runtime execution.

WORKDIR /app
CMD ["/app/init-container.sh"]
