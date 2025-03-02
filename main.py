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
)


# Create callback data
class TtCallback(CallbackData, prefix="tt"):
    action: str
    user_id: int
    message_id: int


# Create State to reply to the video
class TtState(StatesGroup):
    reply_to_video = State()


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


# Download a tiktok video and return the filename
async def download_tiktok(url: str) -> str:
    # Run the synchronous save_tiktok function in a separate thread
    vid_fn = await asyncio.to_thread(pyk.save_tiktok, url, True, 'chrome', return_fns=True)
    return vid_fn['video_fn']

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
    await message.answer(f"⚠ {html.underline('наразі йде бета тестування!!')}\n\n👋 {html.bold('всєм прівєт, цей мій тікіток ботік.')} \n\nщоб ви могли скинути посилання на відік, а мені не прийшлося б потім страждати і відкривати його в браузері. \n\nвін одразу надішле мені файл і людинку, яка його відправила!")


# If message contains tiktok url, proccess it
@dp.message(F.text.startswith('https://vm.tiktok.com/'))
@dp.message(F.text.startswith('https://www.tiktok.com/'))
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
            await result.reply(f"📼 {html.bold('відео від:')} {html.unparse(user.full_name)}")
        await message.reply("✅ відео надіслано, дякую!!")
    except Exception as e:
        await bot.send_message(ADMIN_ID, f"Error: {e}")
        await message.answer(f"💢 {html.bold('якась ошибка!!!!!')} яна потом пофіксить..")


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
    await message.answer(f"🔗 {html.bold('цей ботік реагує лише на тік-ток відео')}\nздається ви шось не то відправили..")


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())