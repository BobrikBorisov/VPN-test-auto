import requests
import re
import random
import base64
import asyncio

# === 1. ВАШИ ИСТОЧНИКИ (АГРЕГАТОРЫ) ===
# Добавляйте или удаляйте ссылки здесь (каждая ссылка в кавычках, через запятую)
URLS = [
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_base64_Sub.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/python/vless",
    "https://raw.githubusercontent.com/Argh94/Proxy-List/refs/heads/main/All_Config.txt",
    # "СЮДА_МОЖНО_ВСТАВИТЬ_ВАШУ_ССЫЛКУ",
]

# === 2. НАСТРОЙКИ ФИЛЬТРАЦИИ ===
MAX_CONFIGS = 300 
ALLOWED_PORTS = ["443", "80", "8080", "8443", "2053", "2083", "2087", "2096", "11443"]

# Черный список стран (Китай, Иран, Гонконг). Удаляем этот мусор.
BLACKLIST_WORDS = ["CN", "IR", "HK", "CHINA", "IRAN", "ИРАН", "КИТАЙ", "🇮🇷", "🇨🇳", "🇭🇰"]

def decode_base64_robust(data):
    data = data.strip()
    data += "=" * ((4 - len(data) % 4) % 4)
    try:
        return base64.b64decode(data).decode('utf-8', errors='ignore').splitlines()
    except Exception:
        return []

# === 3. АГРЕССИВНЫЙ TCP-ПРОЗВОН ===
sem = asyncio.Semaphore(50)

async def check_port(ip, port, config_line):
    async with sem:
        try:
            # ТАЙМ-АУТ 1.5 СЕКУНДЫ. Все что медленнее - идет в мусорку.
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, int(port)), timeout=1.5
            )
            writer.close()
            await writer.wait_closed()
            return config_line
        except Exception:
            return None

async def verify_configs(parsed_configs):
    print(f">>> Начинаем TCP-прозвон {len(parsed_configs)} серверов (Тайм-аут 1.5с)...")
    tasks = [check_port(ip, port, config) for config, ip, port in parsed_configs]
    
    results = await asyncio.gather(*tasks)
    alive_configs = [res for res in results if res is not None]
    return alive_configs

def process_configs():
    parsed_data = []
    print(">>> Запуск парсера WAP-базы (Строгий Гео-Фильтр)...")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200: continue
            
            content = resp.text.strip()
            lines = content.splitlines() if "vless://" in content[:50] else decode_base64_robust(content)

            for line in lines:
                line = line.strip()
                if len(line) > 1000 or not line.startswith("vless://"): continue
                
                match = re.search(r'@([^:]+):(\d+)\?([^#]+)#(.*)', line)
                if not match: 
                    # Пробуем без ремарки (имени)
                    match = re.search(r'@([^:]+):(\d+)\?([^#]+)', line)
                    if not match: continue
                    remark = ""
                else:
                    remark = match.group(4).upper()

                # --- ГЕО-ФИЛЬТР ---
                # Если в имени есть слова из черного списка - убиваем конфиг
                if any(bad_word in remark for bad_word in BLACKLIST_WORDS):
                    continue
                
                ip = match.group(1)
                port = match.group(2)
                params = match.group(3)
                
                if port not in ALLOWED_PORTS: continue
                
                type_match = re.search(r'type=([^&]+)', params)
                transport = type_match.group(1) if type_match else "tcp"
                if transport not in ["tcp", "ws", "http"]: continue

                parsed_data.append((line, ip, port))

        except Exception as e:
            print(f"[!] Ошибка с {url}: {e}")

    parsed_data = list(set(parsed_data))
    
    # Запускаем прозвон
    alive_configs = asyncio.run(verify_configs(parsed_data))
    print(f">>> Выжило после Агрессивного прозвона: {len(alive_configs)} узлов")

    if len(alive_configs) == 0:
        print("[!] ОШИБКА: Жесткий фильтр убил все сервера. Добавьте больше URL источников.")
        return

    random.shuffle(alive_configs)
    if len(alive_configs) > MAX_CONFIGS:
        alive_configs = alive_configs[:MAX_CONFIGS]

    final_text = "\n".join(alive_configs)
    final_base64 = base64.b64encode(final_text.encode('utf-8')).decode('utf-8')
    
    with open("wap_sub.txt", "w", encoding="utf-8") as f:
        f.write(final_base64)
        
    print(">>> База успешно скомпилирована в wap_sub.txt (Base64)")

if __name__ == "__main__":
    process_configs()
