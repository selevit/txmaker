FROM python:3.7-alpine3.9
MAINTAINER Sergey Levitin <selevit@gmail.com>

RUN addgroup -g 10001 app && adduser -u 10001 -D -h /app -G app app

COPY Pipfile /app
COPY Pipfile.lock /app
WORKDIR /app

RUN set -x && \
    apk add --no-cache --update -t .build-deps build-base postgresql-dev linux-headers \
                                               gcc musl-dev libffi-dev && \
    pip install --no-cache-dir --disable-pip-version-check --upgrade pip==19.1 && \
    pip install --no-cache-dir --disable-pip-version-check --upgrade pipenv==2018.11.26 setuptools==41.0.1 && \
    pipenv install --verbose --system --deploy && \
    runDeps="$( \
      scanelf --needed --nobanner --recursive /usr/local/lib/python3.7 \
        | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
        | sort -u \
        | xargs -r apk info --installed \
        | sort -u \
    )" && \
    pip uninstall -y pipenv && \
    apk add --no-cache -t .run-deps $runDeps && \
    apk del .build-deps

COPY . /app

RUN set -x \
    chmod -R a+rX /app && \
    find . -name '__pycache__' -type d | xargs rm -rf && \
    python -c 'import compileall, os; compileall.compile_dir(os.curdir, force=1)' && \
    chown -R app:app /app

USER app
EXPOSE "8080"
CMD ["python", "main.py"]

ARG APP_VERSION
ENV APP_VERSION ${APP_VERSION:-local_commit}
