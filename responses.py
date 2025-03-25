# functionaliy for how chat responds from user input 

import requests
from random import choice, randint

#Using OpenWeatherMap
def retrieve_weather(city: str, api_key: str) -> str:
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric"
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        weather = data["weather"][0]["description"]
        temperature = data["main"]["temp"]
        temp_in_fahrenheit = round((temperature * 1.8) + 32, 2)
        return f"The weather in {city} is {weather} with a temperature of {temp_in_fahrenheit}°F."
    else:
        return "Sorry, I could not get the weather for the location you provided. Try again, please"

def get_response(user_input: str) -> str:
    lowered: str = user_input.lower()

    if lowered == '':
        return 'Well, youre awfully silent...'
    elif 'hello' in lowered:
        return 'Hey!'
    elif 'how are you' in lowered:
        return 'Good, thanks'
    elif 'bye' in lowered:
        return 'See you!'
    elif 'roll dice' in lowered:
        return f'You rolled: {randint(1,6)}'
    elif 'kys' in lowered:
        return choice (['Nah.',
                       'Look whos talkin',
                       'Right back at you'])
    else:
        return choice(['What...?',
                       'What are you even talking about?',
                       'Bruh...'])