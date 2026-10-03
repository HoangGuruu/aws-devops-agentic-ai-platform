FROM python:3.13-slim
WORKDIR /app
COPY agent/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY agent ./agent
COPY docs/runbooks ./docs/runbooks
COPY examples ./examples
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER 1000
ENTRYPOINT ["python", "-m", "agent.cli"]
