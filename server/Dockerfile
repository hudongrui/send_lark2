FROM python:3.12-slim
LABEL authors="dongruihu"

# CONFIG & LOG
# TODO: Update port & log_path if needed.
RUN mkdir -p $LOG_PATH && \
    chmod 755 -R $LOG_PATH

RUN mkdir /app
RUN mkdir /app/db
WORKDIR /app

COPY . .

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt --index-url https://bytedpypi.byted.org/simple/

# ENV
# TODO: Update port & log_path if needed.
ENV PORT=5000
ENV LOG_PATH=$LOG_PATH

ENTRYPOINT [ "bash", "bootstrap.sh" ]
