FROM python:3.13.3-slim AS dependencies
WORKDIR /build
COPY requirements.txt test-requirements.txt ./
RUN pip install --no-cache-dir --require-hashes --prefix=/install -r requirements.txt
FROM dependencies AS test
ENV PYTHONPATH=/install/lib/python3.13/site-packages
RUN pip install --no-cache-dir --require-hashes -r test-requirements.txt
COPY . /app
WORKDIR /app
RUN PYTHONPATH=/install/lib/python3.13/site-packages:. python -m unittest discover -s tests/unit
FROM python:3.13.3-slim
COPY --from=test /install /usr/local
WORKDIR /app
COPY productpage.py ./
COPY templates ./templates
COPY static ./static
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 9080
USER 1000
CMD ["gunicorn", "-b", "0.0.0.0:9080", "productpage:app", "-w", "1", "--threads", "4", "--access-logfile", "-"]
