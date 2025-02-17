""" downloader """


import asyncio
import math
import os
from datetime import datetime
from typing import Tuple, Union
from urllib.parse import unquote_plus

from pySmartDL import SmartDL

from userge import Config, Message, userge
from userge.utils import humanbytes, progress
from userge.utils.exceptions import ProcessCanceled

LOGGER = userge.getLogger(__name__)


@userge.on_cmd(
    "mirror",
    about={
        "header": "Download files to server",
        "usage": "{tr}mirror [url | reply to telegram media]",
        "examples": "{tr}mirror https://speed.hetzner.de/100MB.bin | testing upload.bin. Found file here https://billouetaudrey.site/mirror/",
    },
    check_downpath=True,
)
async def down_load_media(message: Message):
    """download from tg and url"""
    if message.reply_to_message and message.reply_to_message.media:
        resource = message.reply_to_message
    elif message.input_str:
        resource = message.input_str
    else:
        await message.edit("Please read `.help download`", del_in=5)
        return
    try:
        dl_loc, d_in = await handle_download(message, resource)
    except ProcessCanceled:
        await message.edit("`Process Canceled!`", del_in=5)
    except Exception as e_e:  # pylint: disable=broad-except
        await message.err(e_e)
    else:
        await message.edit(f"Downloaded to `{dl_loc}` in {d_in} seconds. Access to https://billouetaudrey.site/mirror")


async def handle_download(
    message: Message, resource: Union[Message, str]
) -> Tuple[str, int]:
    """download from resource"""
    if isinstance(resource, Message):
        return await tg_download(message, resource)
    return await url_download(message, resource)


async def url_download(message: Message, url: str) -> Tuple[str, int]:
    """download from link"""
    await message.edit("`Downloading From URL...`")
    start_t = datetime.now()
    custom_file_name = unquote_plus(os.path.basename(url))
    if "|" in url:
        url, c_file_name = url.split("|", maxsplit=1)
        url = url.strip()
        if c_file_name:
            custom_file_name = c_file_name.strip()
    dl_loc = os.path.join("/mnt/UB", custom_file_name)
    downloader = SmartDL(url, dl_loc, progress_bar=False)
    downloader.start(blocking=False)
    count = 0
    while not downloader.isFinished():
        if message.process_is_canceled:
            downloader.stop()
            raise ProcessCanceled
        total_length = downloader.filesize or 0
        downloaded = downloader.get_dl_size()
        percentage = downloader.get_progress() * 100
        speed = downloader.get_speed(human=True)
        estimated_total_time = downloader.get_eta(human=True)
        progress_str = (
            "__{}__\n"
            + "```[{}{}]```\n"
            + "**Progress** : `{}%`\n"
            + "**URL** : `{}`\n"
            + "**FILENAME** : `{}`\n"
            + "**Completed** : `{}`\n"
            + "**Total** : `{}`\n"
            + "**Speed** : `{}`\n"
            + "**ETA** : `{}`"
        )
        progress_str = progress_str.format(
            "trying to download",
            "".join(
                (
                    Config.FINISHED_PROGRESS_STR
                    for i in range(math.floor(percentage / 5))
                )
            ),
            "".join(
                (
                    Config.UNFINISHED_PROGRESS_STR
                    for i in range(20 - math.floor(percentage / 5))
                )
            ),
            round(percentage, 2),
            url,
            custom_file_name,
            humanbytes(downloaded),
            humanbytes(total_length),
            speed,
            estimated_total_time,
        )
        count += 1
        if count >= Config.EDIT_SLEEP_TIMEOUT:
            count = 0
            await message.try_to_edit(progress_str, disable_web_page_preview=True)
        await asyncio.sleep(10)
    return dl_loc, (datetime.now() - start_t).seconds


async def tg_download(message: Message, to_download: Message) -> Tuple[str, int]:
    """download from tg file"""
    await message.edit("`Downloading From TG...`")
    start_t = datetime.now()
    custom_file_name = "/mnt/UB"
    if message.filtered_input_str:
        custom_file_name = os.path.join(
            "/mnt/UB", message.filtered_input_str.strip()
        )
    dl_loc = await message.client.download_media(
        message=to_download,
        file_name=custom_file_name,
        progress=progress,
        progress_args=(message, "trying to download"),
    )
    if message.process_is_canceled:
        raise ProcessCanceled
    if not isinstance(dl_loc, str):
        raise TypeError("File Corrupted!")
    dl_loc = os.path.join("/mnt/UB", os.path.basename(dl_loc))
    return dl_loc, (datetime.now() - start_t).seconds
