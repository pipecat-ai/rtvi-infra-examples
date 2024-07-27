FROM python:3.12.4-bookworm

# Env
ENV LOG_LEVEL=INFO

# Install Python dependencies
COPY *.py .
COPY ./requirements.txt requirements.txt
RUN pip3 install --no-cache-dir --upgrade -r requirements.txt