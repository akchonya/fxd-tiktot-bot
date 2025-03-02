import asyncio
import logging
import os
import sys
from os import getenv

import pyktok as pyk
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile


# Download a tiktok video and return the filename
async def download_tiktok(url: str) -> str:
    # Run the synchronous save_tiktok function in a separate thread
    vid_fn = await asyncio.to_thread(pyk.save_tiktok, url, True, 'chrome', return_fns=True)
    return vid_fn['video_fn']

# Send the video to a user and delete the video after sending
async def send_video(bot: Bot, vid_fn: str) -> None:
    fs = FSInputFile(vid_fn)
    result = await bot.send_video(chat_id=ADMIN_ID, video=fs)
    os.remove(vid_fn)
    return result


TOKEN = getenv("BOT_TOKEN")
ADMIN_ID = getenv("ADMIN_ID")

# All handlers should be attached to the Router (or Dispatcher)

dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"👋 {html.bold('всєм прівєт, цей мій тікіток ботік.')} \n\nщоб ви могли скинути посилання на відік, а мені не прийшлося б потім страждати і відкривати його в браузері. \n\nвін одразу надішле мені файл і людинку, яка його відправила!")


# If message contains tiktok url, proccess it
@dp.message(F.text.startswith('https://vm.tiktok.com/'))
@dp.message(F.text.startswith('https://www.tiktok.com/'))
async def tiktok_handler(message: Message, bot: Bot) -> None:
    try:
        vid_fn = await download_tiktok(message.text)
        result = await send_video(bot, vid_fn)
        # If there is a username, use it, otherwise use the full name
        user = message.from_user
        if user.username:
            await result.reply(f"📼 {html.bold('відео від:')} @{user.username}")
        else:
            await result.reply(f"📼 {html.bold('відео від:')} {html.unparse(user.full_name)}")
        await message.reply("✅ відео надіслано, дякую!!")
    except Exception as e:
        await bot.send_message(ADMIN_ID, f"Error: {e}")
        await message.answer(f"💢 {html.bold('якась ошибка!!!!!')} яна потом пофіксить..")

@dp.message()
async def echo_handler(message: Message) -> None:
    await message.answer(f"🔗 {html.bold('цей ботік реагує лише на тік-ток відео')}\nздається ви шось не то відправили..")


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())