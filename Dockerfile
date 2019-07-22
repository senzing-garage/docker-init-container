ARG BASE_IMAGE=debian:9
FROM ${BASE_IMAGE}

ENV REFRESHED_AT=2019-07-22

LABEL Name="senzing/init-container" \
      Maintainer="support@senzing.com" \
      Version="1.0.0"

HEALTHCHECK CMD ["/app/healthcheck.sh"]

# Install packages via apt.

RUN apt-get update \
 && apt-get -y install \
      curl \
      jq \
      python \
      wget \
 && rm -rf /var/lib/apt/lists/*

# Set environment variables.

ENV SENZING_ROOT=/opt/senzing

# Copy files from repository.

COPY ./rootfs /

# Runtime execution.

WORKDIR /app
CMD ["/app/init-container.sh"]
