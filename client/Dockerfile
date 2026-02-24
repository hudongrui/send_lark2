FROM python:3.12-slim
LABEL authors="dongruihu"

# CONFIG & LOG
RUN mkdir -p /tmp/send_lark_webhook/log && \
    chmod 755 -R /tmp/send_lark_webhook/log

# Work directory
RUN mkdir /app
WORKDIR /app

COPY . .

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# ENV
ENV PORT=5000
ENV LOG_PATH=/tmp/send_lark_webhook/log

ENTRYPOINT [ "bash", "bootstrap.sh" ]