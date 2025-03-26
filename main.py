import asyncio
import logging
import os
import sys
from os import getenv
import re

import aiohttp
import pyktok as pyk
from playwright.async_api import async_playwright
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReactionTypeEmoji,
    InputMediaPhoto,
)


# Create callback data
class TtCallback(CallbackData, prefix="tt"):
    action: str
    user_id: int
    message_id: int


# Create State to reply to the video
class TtState(StatesGroup):
    reply_to_video = State()


SAVE_DIR = "downloads"
os.makedirs(SAVE_DIR, exist_ok=True)


# Create an inline keyboard
def create_inline_keyboard(user_id: int, message_id: int) -> InlineKeyboardMarkup:
    cb_reply = TtCallback(action="reply", user_id=user_id, message_id=message_id).pack()
    cb_like = TtCallback(action="like", user_id=user_id, message_id=message_id).pack()
    cb_cool = TtCallback(action="cool", user_id=user_id, message_id=message_id).pack()
    cb_cringe = TtCallback(
        action="cringe", user_id=user_id, message_id=message_id
    ).pack()
    cb_slay = TtCallback(action="slay", user_id=user_id, message_id=message_id).pack()

    ikb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💬", callback_data=cb_reply),
                InlineKeyboardButton(text="♥", callback_data=cb_like),
                InlineKeyboardButton(text="😎", callback_data=cb_cool),
                InlineKeyboardButton(text="🥴", callback_data=cb_cringe),
                InlineKeyboardButton(text="💅", callback_data=cb_slay),
            ]
        ]
    )
    return ikb


async def download_file(session, url, filename):
    """Download a file asynchronously and save it."""
    file_path = os.path.join(SAVE_DIR, filename)
    async with session.get(url) as response:
        if response.status == 200:
            with open(file_path, "wb") as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)
            print(f"Downloaded: {filename}")
        else:
            print(f"Failed to download {url}")


async def process_tiktok(url):
    """Process a TikTok URL and download media files."""
    image_urls = []
    audio_urls = []

    async with aiohttp.ClientSession() as session:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            async def intercept_response(response):
                response_url = response.url
                content_type = response.headers.get("content-type", "")

                if "image/jpeg" in content_type or response_url.endswith(".jpeg"):
                    if "avt" in response_url or "cropcenter:100:100" in response_url:
                        print(f"Skipping profile image: {response_url}")
                        return
                    image_urls.append(response_url)

                elif "audio/mpeg" in content_type or response_url.endswith(".mp3"):
                    audio_urls.append(response_url)

            page.on("response", intercept_response)

            print(f"Opening TikTok URL: {url}")
            await page.goto(url, wait_until="networkidle")
            await asyncio.sleep(5)
            await browser.close()

            # Now download files in collected order
            found_files = []

            print("\nDownloading images in order:")
            for idx, img_url in enumerate(image_urls):
                filename = f"image_{idx}.jpeg"
                await download_file(session, img_url, filename)
                found_files.append(filename)

            print("\nDownloading audio:")
            for idx, audio_url in enumerate(audio_urls):
                filename = f"audio_{idx}.mp3"
                await download_file(session, audio_url, filename)
                found_files.append(filename)

            print("\nFiles downloaded in order:")
            for file in found_files:
                print(file)

            return found_files


# Download a tiktok video and return the filename
async def download_tiktok(url: str) -> str:
    # Run the synchronous save_tiktok function in a separate thread
    vid_fn = await asyncio.to_thread(
        pyk.save_tiktok, url, True, "chrome", return_fns=True
    )
    return vid_fn["video_fn"]


# Send the video to a user and delete the video after sending
async def send_video(bot: Bot, vid_fn: str, ikb: InlineKeyboardMarkup) -> None:
    fs = FSInputFile(vid_fn)
    result = await bot.send_video(chat_id=ADMIN_ID, video=fs, reply_markup=ikb)
    os.remove(vid_fn)
    return result


TOKEN = getenv("BOT_TOKEN")
ADMIN_ID = getenv("ADMIN_ID")

# All handlers should be attached to the Router (or Dispatcher)

dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f"⚠ {html.underline('наразі йде бета тестування!!')}\n\n👋 {html.bold('всєм прівєт, цей мій тікіток ботік.')} \n\nщоб ви могли скинути посилання на відік, а мені не прийшлося б потім страждати і відкривати його в браузері. \n\nвін одразу надішле мені файл і людинку, яка його відправила!"
    )


async def send_media_group(bot: Bot, user_id: str, image_files: list[str]) -> None:
    """Send images in groups of 10 (Telegram's limit for media groups), maintaining order"""
    from aiogram.types import InputMediaPhoto

    # Sort files by their index number
    sorted_files = sorted(
        image_files, key=lambda x: int(re.search(r"image_(\d+)", x).group(1))
    )
    print(
        "Files will be sent in this order:", [os.path.basename(f) for f in sorted_files]
    )

    # Process in chunks of 10, maintaining order
    chunks = [sorted_files[i : i + 10] for i in range(0, len(sorted_files), 10)]

    for chunk in chunks:
        # Reverse the chunk if Telegram is displaying them in reverse
        chunk = chunk[::-1]  # This will make image_0 appear first in the album
        print("Sending chunk:", [os.path.basename(f) for f in chunk])
        media_group = [
            InputMediaPhoto(type="photo", media=FSInputFile(img)) for img in chunk
        ]
        await bot.send_media_group(chat_id=user_id, media=media_group)
        await asyncio.sleep(1)


@dp.message(F.text.startswith("https://vm.tiktok.com/"))
@dp.message(F.text.startswith("https://www.tiktok.com/"))
async def tiktok_handler(message: Message, bot: Bot) -> None:
    try:
        vid_fn = await download_tiktok(message.text)
        ikb = create_inline_keyboard(message.from_user.id, message.message_id)
        result = await send_video(bot, vid_fn, ikb)
        # If there is a username, use it, otherwise use the full name
        user = message.from_user
        if user.username:
            await result.reply(f"📼 {html.bold('відео від:')} @{user.username}")
        else:
            await result.reply(
                f"📼 {html.bold('відео від:')} {html.unparse(user.full_name)}"
            )
        await message.reply("✅ відео надіслано, дякую!!")
    except KeyError:
        # Send a message that media is being processed
        await message.reply("🔄 медіа завантажується...")
        # Create temporary directory for this user
        temp_dir = f"downloads/{message.from_user.id}"
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # Override global SAVE_DIR for this download
            global SAVE_DIR
            original_save_dir = SAVE_DIR
            SAVE_DIR = temp_dir

            # Process TikTok and get files
            found_files = await process_tiktok(message.text)

            # Separate images and audio files
            image_files = [
                os.path.join(temp_dir, f)
                for f in os.listdir(temp_dir)
                if f.startswith("image_")
            ]
            audio_files = [
                os.path.join(temp_dir, f)
                for f in os.listdir(temp_dir)
                if f.startswith("audio_")
            ]

            # Send images if any
            if image_files:
                await send_media_group(bot, ADMIN_ID, image_files)

            # Send audio if any
            for audio_file in audio_files:
                ikb = create_inline_keyboard(message.from_user.id, message.message_id)
                await bot.send_audio(
                    chat_id=ADMIN_ID, audio=FSInputFile(audio_file), reply_markup=ikb
                )

            # Send user info
            user = message.from_user
            user_info = (
                f"@{user.username}" if user.username else html.unparse(user.full_name)
            )
            await bot.send_message(
                ADMIN_ID, f"📼 {html.bold('медіа від:')} {user_info}"
            )

            await message.reply("✅ медіа надіслано, дякую!!")

        except Exception as e:
            await bot.send_message(ADMIN_ID, f"Error in process_tiktok: {e}")
            await message.answer(
                f"💢 {html.bold('якась ошибка!!!!!')} яна потом пофіксить.."
            )
        finally:
            # Restore original SAVE_DIR
            SAVE_DIR = original_save_dir
            # Clean up temporary directory
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        await bot.send_message(ADMIN_ID, f"Error: {e}")
        await message.answer(
            f"💢 {html.bold('якась ошибка!!!!!')} яна потом пофіксить.."
        )


@dp.callback_query(TtCallback.filter(F.action == "like"))
async def like_handler(
    callback: CallbackQuery, callback_data: TtCallback, bot: Bot
) -> None:
    await callback.answer("❤‍🔥")
    await bot.set_message_reaction(
        callback_data.user_id,
        callback_data.message_id,
        [ReactionTypeEmoji(emoji="❤‍🔥")],
    )


@dp.callback_query(TtCallback.filter(F.action == "cool"))
async def cool_handler(
    callback: CallbackQuery, callback_data: TtCallback, bot: Bot
) -> None:
    await callback.answer("😎")
    await bot.set_message_reaction(
        callback_data.user_id,
        callback_data.message_id,
        [ReactionTypeEmoji(emoji="😎")],
    )


@dp.callback_query(TtCallback.filter(F.action == "cringe"))
async def cringe_handler(
    callback: CallbackQuery, callback_data: TtCallback, bot: Bot
) -> None:
    await callback.answer("🥴")
    await bot.set_message_reaction(
        callback_data.user_id,
        callback_data.message_id,
        [ReactionTypeEmoji(emoji="🥴")],
    )


@dp.callback_query(TtCallback.filter(F.action == "slay"))
async def slay_handler(
    callback: CallbackQuery, callback_data: TtCallback, bot: Bot
) -> None:
    await callback.answer("💅")
    await bot.set_message_reaction(
        callback_data.user_id,
        callback_data.message_id,
        [ReactionTypeEmoji(emoji="💅")],
    )


@dp.callback_query(TtCallback.filter(F.action == "reply"))
async def reply_handler(
    callback: CallbackQuery, callback_data: TtCallback, bot: Bot, state: FSMContext
) -> None:
    await callback.answer()
    await state.update_data(
        user_id=callback_data.user_id, message_id=callback_data.message_id
    )
    await state.set_state(TtState.reply_to_video)
    await callback.message.reply("💬 напишіть ваше повідомлення:")


@dp.message(TtState.reply_to_video)
async def reply_to_video_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    await bot.send_message(
        data["user_id"],
        f"💬 {html.bold('коментар:')} {message.text}",
        reply_to_message_id=data["message_id"],
    )
    await message.react([ReactionTypeEmoji(emoji="👌")])
    await state.clear()


@dp.message()
async def echo_handler(message: Message) -> None:
    await message.answer(
        f"🔗 {html.bold('цей ботік реагує лише на тік-ток відео')}\nздається ви шось не то відправили.."
    )


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())