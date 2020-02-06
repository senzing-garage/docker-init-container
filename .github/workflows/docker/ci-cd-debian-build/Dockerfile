FROM senzing/base-image-debian:1.0.0

ARG GITHUB_HEAD_REF="master"
ARG GITHUB_OWNER="Senzing"
ARG GITHUB_EVENT_NAME="push"
ARG SENZING_REPO_URL="https://senzing-production-apt.s3.amazonaws.com/senzingrepo_1.0.0-1_amd64.deb"

LABEL Name="senzing-ci-cd-debian-builder" \
      Maintainer="support@senzing.com" \
      Version="1.0.0"

# Set environment variables.
ENV SENZING_ACCEPT_EULA=I_ACCEPT_THE_SENZING_EULA

# Add Senzing Files
RUN wget ${SENZING_REPO_URL} \
    && apt-get -y install ./${SENZING_REPO_URL##*/} \
    && apt-get -y update \
    && rm -rf senzingrepo_1.0.0-1_amd64.deb

# Set environment variables.
ENV SENZING_DATA_VERSION_DIR=/opt/senzing/data/1.0.0
ENV SENZING_ETC_DIR=/etc/opt/senzing
ENV SENZING_G2_DIR=/opt/senzing/g2
ENV SENZING_VAR_DIR=/var/opt/senzing

# Clone Senzing Init Container repository.
WORKDIR /
RUN git clone https://github.com/${GITHUB_OWNER}/docker-init-container.git

# Build Senzing Init Container
WORKDIR /docker-init-container
RUN git checkout ${GITHUB_HEAD_REF}; \
    if [[ "${GITHUB_HEAD_REF}" != "master" && ${GITHUB_EVENT_NAME} == "pull_request" ]]; then \
        git merge issue-41.mahchiahui.1; \
    fi

WORKDIR /docker-init-container
RUN initialize