FROM python:3.12.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN pip install -e .

RUN adduser --disabled-password --gecos "" eidolon
USER eidolon

ENV PYTHONPATH=/app

# Default command runs the main application
# Can be overridden with CLI commands like:
# docker run -it --rm image_name eidolon list modules
ENTRYPOINT ["python", "-m"]
CMD ["main"]
