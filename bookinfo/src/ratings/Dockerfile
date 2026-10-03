FROM node:22-bookworm-slim

#hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install curl ca-certificates --no-install-recommends -y \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG service_version
ENV SERVICE_VERSION=${service_version:-v1}

COPY package*.json /opt/microservices/
COPY ratings.js /opt/microservices/
WORKDIR /opt/microservices
RUN npm ci --omit=dev

EXPOSE 9080
CMD ["node", "/opt/microservices/ratings.js", "9080"]

USER 1000
