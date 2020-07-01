FROM python:3.7

ARG SHOTGUN_EVENTS_PATH=/usr/local/shotgun/shotgunEvents
WORKDIR ${SHOTGUN_EVENTS_PATH}
COPY src src
COPY requirements.txt .
COPY setup.py .

RUN pip install -U pip && pip install -r requirements.txt

VOLUME ${SHOTGUN_EVENTS_PATH}

ENTRYPOINT [ "shotgunEventDaemon" ]
CMD [ "foreground" ]


# RUN_ARGS=(-v "$(pwd)":"/usr/local/shotgun/shotgunEvents":ro "local/shotgunEventDaemon")
# docker run --rm -it "${RUN_ARGS[@]}" --help

# # Either one of...
# docker run --rm -it "${RUN_ARGS[@]}"  # Interactive foreground
# docker run --rm -d "${RUN_ARGS[@]}"  # Non-interactive background

# # From another terminal...
# docker logs --follow RUNNING_CONTAINER  # can also "--tail 20" to not be overwhelmed
# docker exec -it RUNNING_CONTAINER stop
# docker exec -it RUNNING_CONTAINER restart