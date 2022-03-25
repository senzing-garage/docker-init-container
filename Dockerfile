ARG BASE_IMAGE=debian:11.2-slim@sha256:4c25ffa6ef572cf0d57da8c634769a08ae94529f7de5be5587ec8ce7b9b50f9c
FROM ${BASE_IMAGE}

ENV REFRESHED_AT=2022-03-17
ENV SENZING_API_SERVER_KEY_STORE_PASSWORD=change-it
ENV SENZING_API_SERVER_CLIENT_KEY_STORE_PASSWORD=change-it

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
      libaio1 \
      libssl1.1 \
      odbc-postgresql \
      python3 \
&& rm -rf /var/lib/apt/lists/*

# Copy files from repository.

COPY ./rootfs /
COPY ./init-container.py /app/

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

# Generate server and client keystore

RUN keytool -genkey -alias sz-api-server -keystore sz-api-server-store.p12 -storetype PKCS12 -keyalg RSA -storepass '$SENZING_API_SERVER_CLIENT_KEY_STORE_PASSWORD' -validity 730 -keysize 2048 -dname 'CN=Unknown, OU=Unknown, O=Unknown, L=Unknown, ST=Unknown, C=Unknown' \
      && keytool -genkey -alias my-client -keystore my-client-store.p12 -storetype PKCS12 -keyalg RSA -storepass '$SENZING_API_SERVER_CLIENT_KEY_STORE_PASSWORD' -validity 730 -keysize 2048 -dname 'CN=Unknown, OU=Unknown, O=Unknown, L=Unknown, ST=Unknown, C=Unknown' \
      && keytool -export -keystore my-client-store.p12 -storepass '$SENZING_API_SERVER_CLIENT_KEY_STORE_PASSWORD' -storetype PKCS12 -alias my-client -file my-client.cer \
      && keytool -import -file my-client.cer -alias my-client -keystore client-trust-store.p12 -storetype PKCS12 -storepass '$SENZING_API_SERVER_CLIENT_KEY_STORE_PASSWORD' -noprompt \
      && export SENZING_API_SERVER_KEY_STORE_BASE64_ENCODED=(base64 sz-api-server-store.p12) \
      && export SENZING_API_SERVER_CLIENT_KEY_STORE_BASE64_ENCODED=(base64 client-trust-store.p12)

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
