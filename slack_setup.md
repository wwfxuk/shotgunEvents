# Setting up Slack

Forked from [chickenbone's fork], these instructions are for how to
get a daemon up and running with Slack plugin.

These instructions are primarily for Linux, but can also adapted for Windows
or Mac.


## Requirements

- Git
- Python 3.7 or Docker.

To use the latest [Slack Python API], Python >= 3.6 is required so why not use
Python 3.7 :P

Docker can be used to perform Python 3.7 actions e.g. mount current source
folder using [--volume flag]. Docker can also, run the daemon in
an isolated environment with required packages setup, but you could also do
the same with a [Python venv].


## Repository setup

Here we will update setup the source code needed before actually running the
daemon.

### Cloning

Assuming we're in an **empty** folder where the source code of `shotgunEvents`
will be in:

```bash
git clone https://github.com/chicken-bone/shotgunEvents.git .
git remote add sg https://github.com/shotgunsoftware/shotgunEvents.git
git remote update
```

You should now be checked out at the latest `chicken-bone` default branch and
also have the official `shotgunsoftware` fork available as a remote named
`sg`.

### Updating source code

We'll be using the latest and greatest available code at the time of writing,
30 June 2020, mainly to make it work for Python 3.7.

At time of writing:

- `adece63`: latest commit on `chicken-bone`'s `master`
- `sg/black`: latest `shotgunsoftware` branch

We'll:

1. Create a squashed commit of [chicken-bone's fork]'s changes
1. Rebase on top of `sg/black`, fix any conflicts
1. Update code to run on Python 3.7
1. Switch to Slack API v2


#### Updating

```bash
# --- Create squashed commit ---
git checkout -b chickenbone-adece63 adece63
COMMON_PARENT="$(git show --format='%h' --no-patch $(git merge-base adece63 sg/black))"
git reset "$COMMON_PARENT"
git add .
git commit -m "Squashed $COMMON_PARENT..adece63"

# --- Rebasing ---
git rebase sg/black
```

Now you would need to fix any conflicts and save the files. Then:

```bash
git add .
git rebase --continue

# --- Update to Python 3.7 ---
# Docker equivalent if you don't have "python3.7" available locally (not tested):
# docker run --rm -it -v "$(pwd)":"$(pwd)" -u "$(id -u):$(id -g)" -w "$(pwd)" python:3.7 2to3-3.7 -wn .
2to3-3.7 -wn .
git add .
git commit -m 'Ran "2to3-3.7 -wn ."'
```

#### Slack API v2

The current source code at [chickenbone's fork] uses the old Slack API v1.
we would then need to update the calls to use `slack.WebClient` instead of
`slackclient.SlackClient`.

I also took this opportunity to update the formatting and code style.

```python
from slack import WebClient

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_USER_TOKEN = os.environ["SLACK_USER_TOKEN"]
SLACK_BOT_USER_ID = os.environ["SLACK_BOT_USER_ID"]
SC_BOT = WebClient(token=SLACK_BOT_TOKEN)
SC_USER = WebClient(token=SLACK_USER_TOKEN)
```

## Running daemon


`requirements.txt`

```
slackclient
git+git://github.com/shotgunsoftware/python-api.git
```

```bash
pip install -r requirements.txt
```

### Docker

Build from repository root:

```bash
IMAGE_TAG="local/shotgun_event_daemon"
docker build --rm --tag "$IMAGE_TAG" .
```

First prepare mount of our code, then running:

```bash
RUN_ARGS=(--rm)
RUN_ARGS+=(--env "SG_SERVER=https://yoursite.shotgunstudio.com")
RUN_ARGS+=(--env "SG_SCRIPT_NAME=Shotgun ApiUser.firstname")
RUN_ARGS+=(--env "SG_SCRIPT_KEY=abcdefg1234567890_abcdefg")  # Make sure to (re)generate one without %
RUN_ARGS+=(--env "SLACK_USER_TOKEN=xoxp-123456789012-123456789012-1234567890123-1234567890abcdef1234567890abcdef")
RUN_ARGS+=(--env "SLACK_BOT_TOKEN=xoxb-123456789012-1234567890123-abcdeABCDE12345abcdeABCD")
RUN_ARGS+=(--env "SLACK_BOT_APP_ID=ABCDEFG1234")
RUN_ARGS+=(--volume "$(pwd)":"/usr/local/shotgun/shotgunEvents":ro)
RUN_ARGS+=("$IMAGE_TAG")
docker run -it "${RUN_ARGS[@]}" --help

# Either one of...
docker run -it "${RUN_ARGS[@]}"  # Interactive foreground
docker run -d "${RUN_ARGS[@]}"  # Non-interactive background
```

Checking logs, Stopping, Restarting from another terminal:

```bash
docker logs --follow RUNNING_CONTAINER  # can also "--tail 20" to not be overwhelmed
docker exec -it RUNNING_CONTAINER stop
docker exec -it RUNNING_CONTAINER restart
```






[chickenbone's fork]: https://github.com/chicken-bone/shotgunEvents/tree/adece63
[Slack Python API]: https://github.com/slackapi/python-slackclient
[--volume flag]: https://docs.docker.com/engine/reference/commandline/run/#mount-volume--v---read-only
[Python venv]: https://docs.python.org/3.7/library/venv.html
[setup.py]: https://github.com/bpabel/shotgunEvents/tree/ad255ec938cd30fccfa4f35158014a6ebcab5864
