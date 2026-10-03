FROM ruby:3.4.3-slim

WORKDIR /opt/microservices
COPY Gemfile /opt/microservices/
RUN bundle install

COPY details.rb /opt/microservices/

ARG service_version
ENV SERVICE_VERSION=${service_version:-v1}
ARG enable_external_book_service
ENV ENABLE_EXTERNAL_BOOK_SERVICE=${enable_external_book_service:-false}

EXPOSE 9080

CMD ["ruby", "details.rb", "9080"]

USER 1000
