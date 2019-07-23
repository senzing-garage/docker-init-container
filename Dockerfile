ARG BASE_IMAGE=senzing/senzing-base:latest
FROM ${BASE_IMAGE}

ENV REFRESHED_AT=2019-07-23

LABEL Name="senzing/init-container" \
      Maintainer="support@senzing.com" \
      Version="1.0.0"

HEALTHCHECK CMD ["/app/healthcheck.sh"]

# Copy files from repository.

COPY ./rootfs /

# Runtime execution.

WORKDIR /app
CMD ["/app/init-container.sh"]
