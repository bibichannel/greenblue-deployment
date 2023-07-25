FROM python:3.12.0b4-slim-bullseye

ARG STAGE="development"

ARG PORT=4000

ENV NODE_ENV=${STAGE}

COPY . /app

RUN chmod +x entrypoint.sh

EXPOSE ${PORT}

CMD ["/bin/sh", "-c", "./entrypoint.sh"]