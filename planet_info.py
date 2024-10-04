import anthropic
import glob
import base64
from tqdm import tqdm
import json
import sqlite3
from PIL import Image
import io
import random
import math

def generate_planet_info():
    # 직경 (km)
    diameter = round(random.uniform(1000, 200000), -2)
    
    # 질량 (kg)
    mass_exp = random.randint(20, 27)
    mass = round(random.uniform(1, 9.99), 2) * (10 ** mass_exp)
    
    # 공전 주기 (지구일)
    orbital_period = round(random.uniform(10, 90000), -1)
    
    # 자전 주기 (시간)
    rotation_period = round(random.uniform(1, 1000), 1)
    
    # 평균 온도 (섭씨)
    avg_temp_c = round(random.uniform(-200, 500), 1)
    avg_temp_f = round(avg_temp_c * 9/5 + 32, 1)
    
    # 확률
    probability = random.randint(0, 10000)
    
    return {
        "diameter": f"{diameter:,} km",
        "mass": f"{mass:.3e} kg",
        "orbitalPeriod": f"{orbital_period:,} Earth days",
        "rotationPeriod": f"{rotation_period:,} hours",
        "averageTemp": f"{avg_temp_c:,}°C ({avg_temp_f:,}°F)",
        "probability": probability
    }

client = anthropic.Anthropic()

DB_FILE = "db.sqlite3"
planet_list = sorted(glob.glob("static/planets2/*.png"))

names = []

for planet_path in tqdm(planet_list):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM planets WHERE path = ?
    ''', (f"/{planet_path}",))
    if cursor.fetchone():
        conn.close()
        continue

    # 이미지 열기 및 리사이즈
    with Image.open(planet_path) as img:
        img = img.resize((128, 128))
        
        # 리사이즈된 이미지를 바이트로 변환
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_byte = buffered.getvalue()
        
        # 인코딩
        encoded_img = base64.b64encode(img_byte).decode()

    names_str = ", ".join(names)

    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": encoded_img
                        }
                    },
                    {
                        "type": "text",
                        "text": f"""Based on the image provided, create a detailed description of the planet. Include its physical characteristics, potential composition, and any unique features visible. Also, suggest a creative and unique name for the planet. Finally, provide this information in a JSON format with both English and Korean translations. Do not include any explanatory text outside of the JSON object in your response. funFact를 제외한 필드는 명사형 종결어미를 사용하여 명사형으로 만들어야 함. funFact는 정말 재미있고 흥미로운 사실을 상상하여 쓰세요. "Be creative and detailed!".

Example:
{{
    "en": {{
        "name": "Don't use the same name as following list: {names_str}",
        "composition": "",
        "atmosphere": "",
        "features": "",
        "moons": "Based on the planet's appearance and type, imagine a realistic number and type of moons. Consider the planet's size, composition, and potential formation history.",
        "planetType": "Based on the visual characteristics of the planet image, select at least 2 appropriate types from the following list. Consider color, texture, and any visible features when making your selection: Asteroids, Barren, Moon, Black holes, Comets, Desert, Martian, Dyson sphere, Forest, Jungle, Swamp, Gas Giant, Toxic, Galaxies, Ice, Snow, Lava, Small moon, Nebulae, Ocean, Pulsars, Quasars, Rings, Rocky, Starfield, Sun, Supernova, Terran/Earth-like, Tech/Death star, Tundra, Rocky",
        "lifeChance": "",
        "funFact": ""
    }},
    "ko": {{
        "name": "한국어로 발음할 수 있으면 한국어로 쓰고 불가능하면 영어로 쓰세요.",
        "composition": "",
        "atmosphere": "",
        "features": "",
        "moons": "",
        "planetType": "",
        "lifeChance": "",
        "funFact": ""
    }}
}}"""
                    }
                ]
            }
        ],
        max_tokens=4096,
        temperature=0.9,
    )

    info = json.loads(message.content[0].text)

    generated_info = generate_planet_info()

    # info에 generated_info 추가
    for key, value in generated_info.items():
        info["en"][key] = value
        info["ko"][key] = value

    # 한국어 번역이 필요한 키들
    ko_translations = {
        "orbitalPeriod": "지구일",
        "rotationPeriod": "시간",
        "averageTemp": "°C"
    }

    # 한국어 번역 적용
    for key, unit in ko_translations.items():
        if key in info["ko"]:
            info["ko"][key] = info["ko"][key].replace("Earth days", unit).replace("hours", unit)

    print(names_str)
    print(info)

    cursor.execute('''
    INSERT INTO planets (name, path, info, probability) VALUES (?, ?, ?, ?)
    ''', (info["en"]["name"], f"/{planet_path}", json.dumps(info, ensure_ascii=False), info["en"]["probability"]))
    conn.commit()
    conn.close()

    names.append(info["en"]["name"])


