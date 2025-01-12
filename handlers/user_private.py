import os
import requests
from datetime import datetime

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types.input_file import BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from googletrans import Translator

from database import get_db
from models import CityForecast, ForecastDetails, WeatherIcons
from country_codes import country_codes
from kbds.reply import start_kb
from wikipedia_get_climate import get_climate

from dotenv import load_dotenv

load_dotenv()

api_key_weather = os.getenv("API_KEY_WEATHER")

user_private_router = Router()

class GetWeather(StatesGroup):
    country_name = State()
    city_name = State()


def get_wind_direction(degree):
    """Определение направления ветра на основе градуса"""
    directions = [
        "Север (N)", "Северо-восток (NE)", "Восток (E)",
        "Юго-восток (SE)", "Юг (S)", "Юго-запад (SW)",
        "Запад (W)", "Северо-запад (NW)"
    ]
    index = int((degree + 22.5) / 45) % 8  # Нахождение индекса по значению градуса
    return directions[index]


@user_private_router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    await message.answer(
        "Привет! Вас приветствует бот прогноза погоды☀️⛈️❄️🌈\nНажмите на кнопку 'Узнать прогноз погоды', чтобы начать.",
        reply_markup=start_kb
    )


@user_private_router.message(F.text == "Узнать прогноз погоды")
async def ask_country(message: types.Message, state: FSMContext):
    """Обработчик кнопки 'Узнать прогноз погоды'"""
    await message.delete()
    await message.answer("Введите название страны:")
    await state.set_state(GetWeather.country_name)


@user_private_router.message(GetWeather.country_name, F.text)
async def set_country_name(message: types.Message, state: FSMContext):
        translator = Translator()
        country_name_ru = message.text.strip()

        # Перевод названия страны на английский, чтобы найти ее код
        country_name_en = (await translator.translate(country_name_ru, src="ru", dest="en")).text

        country_code = next((item["alpha-2"] for item in country_codes if item["name"].lower() == country_name_en.lower()), None)
        if not country_code:
            await message.answer("Страна не найдена. Попробуйте снова.")
            return

        await state.update_data(country_name=country_name_ru, country_code=country_code)
        await message.answer("Введите название города:")
        await state.set_state(GetWeather.city_name)


@user_private_router.message(GetWeather.city_name, F.text)
async def get_weather_data(message: types.Message, state: FSMContext):
    """Получение данных о погоде и сохранение в базу данных"""
    user_data = await state.get_data()
    city_name = message.text.strip()
    country_code = user_data["country_code"]

    # Запрос к OpenWeatherMap для получения координат города
    response = requests.get(f"http://api.openweathermap.org/geo/1.0/direct?q={city_name},{country_code}&appid={api_key_weather}")
    city_data = response.json()

    if not city_data:
        await message.answer(f"Город {city_name} не найден. Попробуйте снова.")
        return

    # Извлечение данных города
    city = city_data[0]['local_names']['ru']
    region = city_data[0].get("state", "")

    translator = Translator()
    region_ru = (await translator.translate(region, src="en", dest="ru")).text if region else "Без области"

    # Сохранение данных в состоянии
    await state.update_data(city_name=city, region_name=region_ru)

    # Получение прогноза погоды
    lat, lon = city_data[0]['lat'], city_data[0]['lon']
    weather_data = requests.get(
        f'https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key_weather}'
    ).json()

    async with get_db() as session:
        for forecast in weather_data['list']:
            forecast_datetime = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
            
            # Проверка на существование записи
            date_query = select(CityForecast).where(
                CityForecast.city == city,
                CityForecast.country == user_data["country_name"],
                CityForecast.region == region_ru,
                CityForecast.date_time == forecast_datetime
            )
            result = await session.execute(date_query)
            existing_record = result.scalar_one_or_none()

            if existing_record:  
                continue

            # Сохранение данных о городе и прогнозе
            city_forecast = CityForecast(
                city=city,
                country=user_data["country_name"],
                region=region_ru,
                date_time=forecast_datetime
            )
            session.add(city_forecast)
            await session.flush()  # Генерация ID

            # Сохранение деталей прогноза
            icon_code = forecast['weather'][0]['icon']
            icon = await session.execute(select(WeatherIcons).where(WeatherIcons.icon_code == icon_code))
            icon = icon.scalars().first()
            if not icon:
                icon_url = f'https://openweathermap.org/img/wn/{icon_code}@2x.png'
                image_data = requests.get(icon_url).content
                icon = WeatherIcons(icon_code=icon_code, image_data=image_data)
                session.add(icon)
                
            forecast_details = ForecastDetails(
                city_forecast_id=city_forecast.id,
                temperature=forecast['main']['temp'],
                feels_like=forecast['main']['feels_like'],
                cloudiness=forecast['weather'][0]['description'],
                humidity=forecast['main']['humidity'],
                pressure=forecast['main']['pressure'],
                wind_speed=forecast['wind']['speed'],
                wind_direction=get_wind_direction(forecast['wind']['deg']),
                visibility=forecast.get('visibility', None),
                precipitation=str(forecast.get('rain', {}).get('3h', 0) or forecast.get('snow', {}).get('3h', 0)),
                icon_code=icon_code
            )
            session.add(forecast_details)

        await session.commit()

    await message.answer(f"Найден город: {city}\nОбласть: {region_ru}")

    # Вывод прогноза погоды
    await display_weather_forecast(message, city, user_data["country_name"], region_ru)
    await message.answer(
        "Прогноз погоды получен! Вы можете нажать 'Узнать прогноз погоды' для нового запроса.",
        reply_markup=start_kb
    )

    await state.clear()  


async def display_weather_forecast(message: types.Message, city: str, country: str, region: str):
    """Вывод прогноза погоды из базы данных"""
    current_datetime = datetime.now()

    async with get_db() as session:
        query = (
            select(CityForecast)
            .where(
                CityForecast.city == city,
                CityForecast.country == country,
                CityForecast.region == region,
                CityForecast.date_time >= current_datetime
            )
            .options(selectinload(CityForecast.forecast_details))
            .order_by(CityForecast.date_time)
        )
        result = await session.execute(query)
        forecasts = result.scalars().all()

    if not forecasts:
        await message.answer(f"Прогноз погоды для города {city} ({region}, {country}) не найден.")
        return

    # Формирование и вывод прогноза
    forecast_messages = []
    for forecast in forecasts:
        if not forecast.forecast_details:
            continue
        

        details = forecast.forecast_details[0]
        translator = Translator()
        cloudiness = (await translator.translate(details.cloudiness, src="en", dest="ru")).text

        forecast_text = (
            f"{forecast.date_time.strftime('%d.%m.%Y %H:%M')}\n"
            f"Температура: {details.temperature - 273.15:.1f}°C, "
            f"Ощущается как: {details.feels_like - 273.15:.1f}°C\n"
            f"Облачность: {cloudiness}\n"
            f"Влажность: {details.humidity}%\n"
            f"Давление: {details.pressure} гПа\n"
            f"Ветер: {details.wind_speed} м/с ({details.wind_direction})\n\n"
        )
        forecast_messages.append(forecast_text)

    max_message_length = 4096
    current_message = ""
   
    messages = get_climate(city, max_message_length)
    for msg in messages:
        await message.answer(msg)

    for forecast in forecast_messages:
        if len(current_message) + len(forecast) > max_message_length:
            await message.answer(current_message)
            current_message = forecast
        else:
            current_message += forecast
    if current_message:
        await message.answer(current_message)