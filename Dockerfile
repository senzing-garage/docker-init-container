ARG BASE_IMAGE=senzing/senzing-base:1.2.1
FROM ${BASE_IMAGE}

ENV REFRESHED_AT=2019-08-05

LABEL Name="senzing/init-container" \
      Maintainer="support@senzing.com" \
      Version="1.2.1"

HEALTHCHECK CMD ["/app/healthcheck.sh"]

# Run as "root" for system installation.

USER root

# Copy files from repository.

COPY ./rootfs /
COPY init-container.py /app

# Runtime execution.

WORKDIR /app
ENTRYPOINT ["/app/init-container.py"]
CMD ["initialize"]
