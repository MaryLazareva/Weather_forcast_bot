import wikipedia
import re


def get_climate(city_name: str, max_length: int):
    wikipedia.set_lang("ru")
    try:
        page = wikipedia.page(city_name)  # поиск статьи о городе
        content = page.content

        # Поиск раздела "Климат" в статье
        if "Климат" in content:
            start_index = content.find("Климат")
            climate_section = content[start_index:]

            # Ограничим текст до следующего заголовка (начинается с === или ==)
            end_index = climate_section.find("\n==")
            if end_index != -1:
                climate_section = climate_section[:end_index]

            climate_section = climate_section.strip()
            climate_section = re.sub(r"^[,]?\s*Климат\s*={1,3}\s*", "", climate_section)

            # Разделение текста на части по длине, чтобы обойти ограничение отправки сообщений в Телеграмм
            chunks = []
            while len(climate_section) > max_length:
                split_index = climate_section[:max_length].rfind("\n")  
                
                if split_index == -1:
                    split_index = climate_section[:max_length].rfind(" ")

                if split_index == -1:
                    split_index = max_length

                chunks.append(climate_section[:split_index].strip())
                climate_section = climate_section[split_index:].strip()
            chunks.append(climate_section)  

            return [f"Описание климата для города {city_name}:\n\n{chunk}" for chunk in chunks]
        else:
            return [f"Описание климата для города {city_name} не найден."]
    except wikipedia.exceptions.PageError:
        return [f"Статья для {city_name} не найдена."]
