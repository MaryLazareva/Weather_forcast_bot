import os
import asyncio
import requests
from sqlalchemy import select
from database import get_db
from models import CityForecast, ForecastDetails, WeatherIcons

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

api_key_weather = os.getenv("API_KEY_WEATHER")
city = 'Moscow'

async def get_and_save_weather_data():
    """Получение и сохранение данных о погоде"""
    city_data = requests.get(f"http://api.openweathermap.org/geo/1.0/direct?q={city}&&appid={api_key_weather}").json()
    # Получение координат города
    lat = city_data[0]['lat']
    lon = city_data[0]['lon']
    # Получение данных прогноза погоды
    weather_data = requests.get(f'https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key_weather}').json()
    print(weather_data)

    async with get_db() as session:
        for forecast in weather_data['list']:
            # Преобразование строки в объект datetime
            forecast_datetime = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
            # Проверка, существует ли запись в базе данных
            date_query = select(CityForecast).where(
                CityForecast.city == city,
                CityForecast.date_time == forecast_datetime
            )
            result = await session.execute(date_query)
            existing_record = result.scalar_one_or_none()

            if existing_record:
                print(f"Прогноз на {forecast_datetime} уже существует. Пропуск.")
                continue

            city_forecast = CityForecast(city=city, date_time=forecast_datetime)
            session.add(city_forecast)
            await session.flush() # Генерируем ID для city_forecast

            # Сохранение иконки (если её нет в базе)
            icon_code = forecast['weather'][0]['icon']
            icon = await session.execute(select(WeatherIcons).where(WeatherIcons.icon_code == icon_code))
            icon = icon.scalars().first()
            if not icon:
                icon_url =  f'https://openweathermap.org/img/wn/{icon_code}@2x.png'
                image_data = requests.get(icon_url).content # Возвращает содержимое ответа запроса в виде байтов
                icon = WeatherIcons(icon_code=icon_code, image_data=image_data)
                session.add(icon)
            
            # Сохранение деталей прогноза
            forecast_details = ForecastDetails(city_forecast_id=city_forecast.id,
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


def get_wind_direction(degree):
    directions = [
            "Север (N)", "Северо-восток (NE)", "Восток (E)",
            "Юго-восток (SE)", "Юг (S)", "Юго-запад (SW)",
            "Запад (W)", "Северо-запад (NW)"
        ]
    
    #  определения индекса направления ветра из списка, где направления делят полный круг (360°) на 8 равных частей, каждая из которых охватывает 45°
    index = int((degree + 22.5) / 45) % 8  # Делим круг на 8 секторов по 45°
    return directions[index]


if __name__ == "__main__":

    asyncio.run(get_and_save_weather_data())