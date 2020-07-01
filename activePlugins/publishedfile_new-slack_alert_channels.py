# -*- coding: utf-8 -*-
"""Message channels when a ``PublishedFile`` entity is created.

"""

import os
from pprint import pprint, pformat
import textwrap

import schema
import shotgun_api3

import slack_shotgun_bot


def registerCallbacks(reg):
    """
    Register our callbacks.

    :param reg: A Registrar instance provided by the event loop handler.
    """

    # Grab authentication env vars for this plugin. Install these into the env
    # if they don't already exist.
    server = os.environ["SG_SERVER"]
    script_name = os.environ["SG_SCRIPT_NAME"]
    api_key = os.environ["SG_SCRIPT_KEY"]

    # User-defined plugin args, change at will.
    args = {
        "Lighting": ["#compositing"],
        "Shot Sculpt": ["#lighting"],
        "Matchmove": ["#anim", "#lighting"],
    }

    # Grab an sg connection for the validator and bail if it fails.
    sg = shotgun_api3.Shotgun(server, script_name=script_name, api_key=api_key)

    # Register our callback with the Shotgun_%s_Change event and tell the logger
    # about it.
    reg.registerCallback(
        script_name,
        api_key,
        slack_notify_publish,
        {"Shotgun_PublishedFile_New".format(**args): None},
        args=args,
    )
    reg.logger.debug("Registered callback %s", slack_notify_publish)


def create_entity_url(entity):
    postfix = "{type}/{id}".format(**entity)
    server_url = os.environ["SG_SERVER"]
    return f"{server_url}/detail/{postfix}"


def create_entity_mrkdwn(entity, name_fmt="{name}"):
    name = name_fmt.format(**entity)
    link = create_entity_url(entity)
    return f"<{link}|{name}>"


def create_slack_publish_payload(channel, published_file):
    author = create_entity_mrkdwn(published_file["created_by"])
    publish = create_entity_mrkdwn(published_file)
    description = published_file.get("description") or "_No Description_"
    version = published_file.get("version_number") or "_No Version_"
    image = published_file.get("image") or ""

    paths = """
    ```
    {path[local_path_linux]}
    ```
    ```
    {path[local_path_windows]}
    ```
    """.format(
        **published_file
    )

    message = f"""
    {publish} version `{version}` by {author}
    > {description}
    {paths}
    """

    message = textwrap.dedent(message).strip()
    payload = {
        "channel": channel,
        "username": "Shotgun Publishes",
        "icon_emoji": ":construction:",
        "text": message,
        "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": message},},],
    }

    if image and "no_preview" not in image:
        payload["blocks"][0]["accessory"] = {
            "type": "image",
            "image_url": f"{image}",
            "alt_text": "PublishedFile.image",
        }

    return payload


def slack_notify_publish(sg, logger, event, args):
    """
    """
    step_field = "task.Task.step.Step.code"
    published_file = sg.find_one(
        event["entity"]["type"],
        [["id", "is", event["entity"]["id"]]],
        fields=[
            step_field,
            "created_by",
            "description",
            "image",
            "name",
            "path",
            "version_number",
        ],
    )
    pprint(published_file)
    publish_step_name = published_file.get(step_field)

    for step_name, channels in args.items():
        if publish_step_name == step_name:
            for channel in channels:
                message = create_slack_publish_payload(channel, published_file)
                pprint(message)
                slack_shotgun_bot.SC_USER.chat_postMessage(**message)
