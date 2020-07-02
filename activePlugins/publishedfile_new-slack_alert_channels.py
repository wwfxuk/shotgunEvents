# -*- coding: utf-8 -*-
"""Message channels when a ``PublishedFile`` entity is created.

"""

import collections.abc
import os
from pprint import pprint, pformat
import textwrap

from schema import Schema, And, Or
import shotgun_api3

import slack_shotgun_bot

STEP_FIELD = "task.Task.step.Step.code"

SEARCH_FIELDS = [
    STEP_FIELD,
    "created_by",
    "description",
    "entity",
    "image",
    "name",
    "path",
    "published_file_type",
    "version_number",
]


class Dict(Schema):
    """Extend ``Schema`` to ignore other keys by default."""

    def __init__(self, mapping, **kwargs):
        """Constructor that passes through args and kwargs to parent."""
        if isinstance(mapping, collections.abc.MutableMapping):
            mapping.update({str: object})
        super().__init__(mapping, **kwargs)


SEND_RULES = {
    Dict({STEP_FIELD: "Lighting"}): ["#compositing"],
    Dict({STEP_FIELD: Or("Shot Sculpt", "Animation", "FX")}): ["#lighting",],
    Dict(
        {
            STEP_FIELD: "Matchmove",
            "published_file_type": Dict({"name": "Camera"}),
            "path": Dict({"name": lambda n: n.endswith(".abc")}),
        }
    ): ["#anim", "#lighting"],
}


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

    # Grab an sg connection for the validator and bail if it fails.
    sg = shotgun_api3.Shotgun(server, script_name=script_name, api_key=api_key)

    # Register our callback with the Shotgun_%s_Change event and tell the logger
    # about it.
    reg.registerCallback(
        script_name,
        api_key,
        slack_notify_publish,
        {"Shotgun_PublishedFile_New": None},
        args=SEND_RULES,
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

    entity = published_file.get("entity", {}).get("name")
    entity = f"for *{entity}* " if entity else ""
    step = published_file.get(STEP_FIELD)
    step = f"from *{step}* " if step else ""

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
    {publish} version `{version}`
    {step}{entity}by {author}
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
    published_file = sg.find_one(
        event["entity"]["type"],
        [["id", "is", event["entity"]["id"]]],
        fields=SEARCH_FIELDS,
    )
    pprint(published_file)

    for rule, channels in args.items():
        if rule.is_valid(published_file):
            for channel in channels:
                message = create_slack_publish_payload(channel, published_file)
                pprint(message)
                pprint(slack_shotgun_bot.SC_USER.chat_postMessage(**message))
