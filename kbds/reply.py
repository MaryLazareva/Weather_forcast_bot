from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


start_kb = ReplyKeyboardMarkup(
    keyboard=[[
        KeyboardButton(text="Узнать прогноз погоды"),]
    ], resize_keyboard=True
)
