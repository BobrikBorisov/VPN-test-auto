import requests
import re
import random
import base64
import asyncio

# === 1 ИСТОЧНИКИ  ===
URLS = [
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_base64_Sub.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/python/vless",
    "https://raw.githubusercontent.com/Argh94/Proxy-List/refs/heads/main/All_Config.txt",
    # "СЮДА_МОЖНО_ВСТАВИТЬ_ВАШУ_ССЫЛКУ",
]

# === 2. СТРОГИЕ ПРАВИЛА WAP-МАРШРУТИЗАЦИИ ===
MAX_CONFIGS = 300 
ALLOWED_PORTS = ["443", "8443", "2053", "2083", "2087", "2096"] # Только HTTPS порты для CONNECT
BLACKLIST_WORDS = ["CN", "IR", "HK", "CHINA", "IRAN", "ИРАН", "КИТАЙ", "🇮🇷", "🇨🇳", "🇭🇰"]

def decode_base64_robust(data):
    data = data.strip()
    data += "=" * ((4 - len(data) % 4) % 4)
    try:
        return base64.b64decode(data).decode('utf-8', errors='ignore').splitlines()
    except Exception:
        return []

# === 3. АСИНХРОННЫЙ ДВИЖОК ПРОЗВОНА ===
sem = asyncio.Semaphore(50)

async def check_port(ip, port, config_line):
    async with sem:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, int(port)), timeout=2.0 # Увеличен таймаут до 2 секунд для реальности
            )
            writer.close()
            await writer.wait_closed()
            return config_line
        except Exception:
            return None

async def verify_configs(parsed_configs):
    tasks = [check_port(ip, port, config) for config, ip, port in parsed_configs]
    results = await asyncio.gather(*tasks)
    return [res for res in results if res is not None]

def process_configs():
    raw_lines_total = 0
    parsed_data = []
    
    print(">>> ИНИЦИАЛИЗАЦИЯ WAP-ПАРСЕРА (GOLDEN STANDARD) <<<")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200: continue
            
            content = resp.text.strip()
            lines = content.splitlines() if "vless://" in content[:50] else decode_base64_robust(content)
            raw_lines_total += len(lines)

            for line in lines:
                line = line.strip()
                if len(line) > 1000 or not line.startswith("vless://"): continue
                
                # Парсинг структуры VLESS
                match = re.search(r'@([^:]+):(\d+)\?([^#]+)#?(.*)', line)
                if not match: continue
                
                ip, port, params, remark = match.groups()
                remark = remark.upper()

                # Правило 1: Гео-фильтр
                if any(bad in remark for bad in BLACKLIST_WORDS): continue
                
                # Правило 2: WAP Порты
                if port not in ALLOWED_PORTS: continue
                
                # Правило 3: Транспорт (Только TCP Reality или WS)
                type_match = re.search(r'type=([^&]+)', params)
                transport = type_match.group(1) if type_match else "tcp"
                if transport not in ["tcp", "ws"]: continue

                parsed_data.append((line, ip, port))

        except Exception as e:
            print(f"[!] Ошибка источника {url}: {e}")

    print(f"\n[СТАТИСТИКА ФИЛЬТРАЦИИ]")
    print(f"Всего скачано строк: {raw_lines_total}")
    
    # Удаляем абсолютные дубликаты
    unique_data = list(set(parsed_data))
    print(f"Осталось после удаления дубликатов и WAP-фильтров: {len(unique_data)}")

    if not unique_data:
        print("[!] База пуста. Сборка остановлена.")
        return

    # Запускаем прозвон
    print(f"\n>>> Начинаем TCP-прозвон {len(unique_data)} узлов...")
    alive_configs = asyncio.run(verify_configs(unique_data))
    
    print(f"=====================================")
    print(f"[+] ВЫЖИЛО ПОСЛЕ ПРОЗВОНА: {len(alive_configs)} узлов")
    print(f"=====================================\n")

    if len(alive_configs) == 0:
        print("[!] ОШИБКА: Нет рабочих серверов.")
        return

    random.shuffle(alive_configs)
    alive_configs = alive_configs[:MAX_CONFIGS]

    final_text = "\n".join(alive_configs)
    final_base64 = base64.b64encode(final_text.encode('utf-8')).decode('utf-8')
    
    with open("wap_sub.txt", "w", encoding="utf-8") as f:
        f.write(final_base64)
        
    print(">>> Элитная WAP-база успешно сохранена!")

if __name__ == "__main__":
    process_configs()
