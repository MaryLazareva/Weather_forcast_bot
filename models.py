from database import Base
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship



class CityForecast(Base):
    __tablename__="city_forecast"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True)
    date_time = Column(DateTime, index=True) # Дата и время прогноза (dt_txt)

    forecast_details = relationship("ForecastDetails", back_populates="city_forecast") # Связь с ForecastDetails


class ForecastDetails(Base):
    __tablename__ = "forecast_details"

    id = Column(Integer, primary_key=True, index=True)
    city_forecast_id = Column(Integer, ForeignKey("city_forecast.id"))  # Связь с таблицей CityForecast
    temperature = Column(Float)  # Температура
    feels_like = Column(Float)  # Ощущаемая температура
    cloudiness = Column(String)  # Облачность
    humidity = Column(Integer)  # Влажность
    pressure = Column(Integer)  # Давление
    wind_speed = Column(Float)  # Скорость ветра
    wind_direction = Column(String)  # Направление ветра
    visibility = Column(Integer)  # Видимость
    precipitation = Column(String)  # Осадки
    icon_code = Column(String, ForeignKey("weather_icons.icon_code"))  # Связь с таблицей WeatherIcons

    city_forecast = relationship("CityForecast", back_populates="forecast_details")  # Связь с CityForecast
    weather_icon = relationship("WeatherIcons")  # Связь с WeatherIcons


class WeatherIcons(Base):
    __tablename__ = "weather_icons"

    id = Column(Integer, primary_key=True, index=True)
    icon_code = Column(String, unique=True, index=True)  # Код иконки, например '13n'
    image_data = Column(LargeBinary)  # Данные изображения в формате байтов
    