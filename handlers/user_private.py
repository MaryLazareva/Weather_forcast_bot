import os
import requests
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types.input_file import BufferedInputFile

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import get_db
from models import CityForecast, ForecastDetails, WeatherIcons
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

api_key_weather = os.getenv("API_KEY_WEATHER")

user_private_router = Router()


def get_wind_direction(degree):
    """Определение направления ветра на основе градуса"""
    directions = [
        "Север (N)", "Северо-восток (NE)", "Восток (E)",
        "Юго-восток (SE)", "Юг (S)", "Юго-запад (SW)",
        "Запад (W)", "Северо-запад (NW)"
    ]
    index = int((degree + 22.5) / 45) % 8  # Нахождение индекса по значению градуса
    return directions[index]


async def get_and_save_weather_data(city: str):
    """Получение и сохранение данных о погоде"""
    # Получение геокоординат города
    city_data = requests.get(
        f"http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={api_key_weather}"
    ).json()
    if not city_data:
        return None

    lat, lon = city_data[0]['lat'], city_data[0]['lon']
    # Получение прогноза погоды для указанных координат
    weather_data = requests.get(
        f'https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key_weather}'
    ).json()

    async with get_db() as session:
        for forecast in weather_data['list']:
            forecast_datetime = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
            date_query = select(CityForecast).where(
                CityForecast.city == city,
                CityForecast.date_time == forecast_datetime
            )
            result = await session.execute(date_query)
            existing_record = result.scalar_one_or_none()

            if existing_record:   # Если запись в БД существует, она не сохраняется. Чтобы не сохранять те же даты
                continue

            city_forecast = CityForecast(city=city, date_time=forecast_datetime)
            session.add(city_forecast)  # Добавления объекта в сессии
            await session.flush() # Отправление изменений из текущей сессии в базу данных, но без выполнения полного коммита и генерация id

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
    return True


@user_private_router.message(Command("start"))
async def start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer("Привет! Отправьте мне название города, чтобы получить прогноз погоды.")


@user_private_router.message()
async def get_weather(message: types.Message):
    """Обработчик сообщения пользователя с названием города"""
    city = message.text.strip()
    updated = await get_and_save_weather_data(city)
    if not updated:
        await message.answer(f"Город {city} не найден. Убедитесь, что название введено корректно.")
        return

    current_datetime = datetime.now()

    async with get_db() as session:
        date_query = (
            select(CityForecast)
            .where(
                CityForecast.city == city,
                CityForecast.date_time >= current_datetime
            )
            .options(selectinload(CityForecast.forecast_details))
            .order_by(CityForecast.date_time)
        )
        result = await session.execute(date_query)
        forecasts = result.scalars().all()

    if not forecasts:
        await message.answer(f"Прогноз погоды для города {city} не найден.")
        return

    for forecast in forecasts:
        if not forecast.forecast_details:
            continue

        details = forecast.forecast_details[0]
        forecast_text = (
            f"{forecast.date_time.strftime('%d.%m.%Y %H:%M')}\n"
            f"Температура: {details.temperature - 273.15:.1f}°C, "
            f"Ощущается как: {details.feels_like - 273.15:.1f}°C\n"
            f"Облачность: {details.cloudiness}, \n"
            f"Влажность: {details.humidity}%\n"
            f"Ветер: {details.wind_speed} м/с ({details.wind_direction})\n"
        )

        # Загрузка иконки из базы данных
        async with get_db() as session:
            icon_stmt = select(WeatherIcons).where(WeatherIcons.icon_code == details.icon_code)
            icon_result = await session.execute(icon_stmt)
            icon = icon_result.scalars().first()

        if icon:
            image_file = BufferedInputFile(file=icon.image_data, filename=details.icon_code)  # Данные изображения в байтах
            
            await message.answer_photo(photo=image_file, caption=forecast_text)
        else:
            await message.answer(forecast_text)