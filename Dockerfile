ARG BASE_IMAGE=debian:11.2-slim@sha256:4c25ffa6ef572cf0d57da8c634769a08ae94529f7de5be5587ec8ce7b9b50f9c
FROM ${BASE_IMAGE}

ENV REFRESHED_AT=2022-03-17

LABEL Name="senzing/init-container" \
      Maintainer="support@senzing.com" \
      Version="1.7.5"

# Define health check.

HEALTHCHECK CMD ["/app/healthcheck.sh"]

# Run as "root" for system installation.

USER root

# Install packages via apt.

RUN apt update \
 && apt -y install \
      gnupg2 \
      libaio1 \
      libssl1.1 \
      odbc-postgresql \
      python3 \
      python3-pip \
      software-properties-common \
      wget \
&& rm -rf /var/lib/apt/lists/*

# Copy files from repository.

COPY ./rootfs /
COPY ./init-container.py /app/
COPY ./requirements.txt /

# Set environment variables for root.

ENV LD_LIBRARY_PATH=/opt/senzing/g2/lib:/opt/senzing/g2/lib/debian:/opt/IBM/db2/clidriver/lib
ENV ODBCSYSINI=/etc/opt/senzing
ENV PATH=${PATH}:/opt/senzing/g2/python:/opt/IBM/db2/clidriver/adm:/opt/IBM/db2/clidriver/bin
ENV PYTHONPATH=/opt/senzing/g2/python
ENV SENZING_ETC_PATH=/etc/opt/senzing

# Install Java 11

RUN wget -qO - https://adoptopenjdk.jfrog.io/adoptopenjdk/api/gpg/key/public > gpg.key \
      && cat gpg.key | apt-key add - \
      && add-apt-repository --yes https://adoptopenjdk.jfrog.io/adoptopenjdk/deb/ \
      && apt update \
      && apt install -y adoptopenjdk-11-hotspot \
      && rm -rf /var/lib/apt/lists/* \
      && rm -f gpg.key

# Install requirements.txt
RUN pip3 install -r requirements.txt

# Make non-root container.

USER 1001:1001

# Set environment variables for USER 1001.

ENV LD_LIBRARY_PATH=/opt/senzing/g2/lib:/opt/senzing/g2/lib/debian:/opt/IBM/db2/clidriver/lib
ENV ODBCSYSINI=/etc/opt/senzing
ENV PATH=${PATH}:/opt/senzing/g2/python:/opt/IBM/db2/clidriver/adm:/opt/IBM/db2/clidriver/bin
ENV PYTHONPATH=/opt/senzing/g2/python
ENV SENZING_DOCKER_LAUNCHED=true
ENV SENZING_ETC_PATH=/etc/opt/senzing

# Set enviroment variables.

ENV SENZING_SUBCOMMAND=initialize

# Runtime execution.

WORKDIR /app
ENTRYPOINT ["/app/init-container.py"]
