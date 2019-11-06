ARG BASE_IMAGE=senzing/senzing-base:1.3.0
FROM ${BASE_IMAGE}

ENV REFRESHED_AT=2019-11-05

LABEL Name="senzing/init-container" \
      Maintainer="support@senzing.com" \
      Version="1.4.0"

HEALTHCHECK CMD ["/app/healthcheck.sh"]

# Run as "root" for system installation.

USER root

# Copy files from repository.

COPY ./rootfs /
COPY init-container.py /app

# Make non-root container.

USER 1001:1001

# Runtime execution.

WORKDIR /app
ENTRYPOINT ["/app/init-container.py"]
CMD ["initialize"]
