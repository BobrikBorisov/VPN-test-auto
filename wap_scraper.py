import requests
import re
import random
import base64
import asyncio

# === 1. МАССОВЫЕ АГРЕГАТОРЫ (10 000+ серверов) ===
URLS = [
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_base64_Sub.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/python/vless",
    "https://raw.githubusercontent.com/Argh94/Proxy-List/refs/heads/main/All_Config.txt",
    # "СЮДА_МОЖНО_ВСТАВИТЬ_ВАШУ_ССЫЛКУ",
]

# === 2. НАСТРОЙКИ ПАРСЕРА ===
MAX_CONFIGS = 500 
# Черный список стран (Китай, Иран) - этот мусор нам не нужен
BLACKLIST_WORDS = ["CN", "IR", "HK", "CHINA", "IRAN", "ИРАН", "КИТАЙ", "🇮🇷", "🇨🇳", "🇭🇰"]
# Убиваем только чистый UDP. Всё остальное WAP пропустит.
FORBIDDEN_TRANSPORTS = ["kcp", "quic"]

def decode_base64_robust(data):
    data = data.strip()
    data += "=" * ((4 - len(data) % 4) % 4)
    try:
        return base64.b64decode(data).decode('utf-8', errors='ignore').splitlines()
    except Exception:
        return []

# === 3. АСИНХРОННЫЙ ДВИЖОК МАССОВОГО ПРОЗВОНА ===
# 100 одновременных потоков. GitHub выдержит, а мы ускорим процесс.
sem = asyncio.Semaphore(100)

async def check_port(ip, port, config_line):
    async with sem:
        try:
            # Тайм-аут 3.5 секунды. Даем шанс серверам с высоким пингом.
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, int(port)), timeout=3.5
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
    parsed_data = []
    print(">>> ИНИЦИАЛИЗАЦИЯ МАССОВОГО WAP-ПАРСЕРА <<<")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200: continue
            
            content = resp.text.strip()
            lines = content.splitlines() if "vless://" in content[:50] else decode_base64_robust(content)

            for line in lines:
                line = line.strip()
                if len(line) > 1000 or not line.startswith("vless://"): continue
                
                # Извлекаем IP, Порт и Название (Remark)
                match = re.search(r'@([^:]+):(\d+)\?([^#]+)#?(.*)', line)
                if not match: 
                    match = re.search(r'@([^:]+):(\d+)\?([^#]+)', line)
                    if not match: continue
                    remark = ""
                else:
                    remark = match.group(4).upper()

                # 1. ГЕО-ФИЛЬТР (Отсекаем Азию и Иран)
                if any(bad in remark for bad in BLACKLIST_WORDS): continue
                
                ip = match.group(1)
                port = match.group(2)
                params = match.group(3)
                
                # 2. ФИЛЬТР ТРАНСПОРТА (Отсекаем UDP)
                type_match = re.search(r'type=([^&]+)', params)
                transport = type_match.group(1) if type_match else "tcp"
                if transport in FORBIDDEN_TRANSPORTS: continue

                # Добавляем в список для прозвона
                parsed_data.append((line, ip, port))

        except Exception as e:
            print(f"[!] Ошибка с источником {url}: {e}")

    # Удаляем абсолютные дубликаты
    unique_data = list(set(parsed_data))
    print(f"\n[+] Собрано уникальных серверов для прозвона: {len(unique_data)}")

    if not unique_data:
        print("[!] База пуста. Сборка остановлена.")
        return

    # Запускаем прозвон
    print(f">>> Запуск тяжелого TCP-сканирования (ожидайте несколько минут)...")
    alive_configs = asyncio.run(verify_configs(unique_data))
    
    print(f"\n=====================================")
    print(f"[+] ВЫЖИЛО ПОСЛЕ ПРОЗВОНА: {len(alive_configs)} узлов")
    print(f"=====================================\n")

    if len(alive_configs) == 0:
        print("[!] ОШИБКА: Нет рабочих серверов.")
        return

    # Перемешиваем и ограничиваем
    random.shuffle(alive_configs)
    alive_configs = alive_configs[:MAX_CONFIGS]

    # Сохраняем в ОБЫЧНЫЙ ТЕКСТ (Plain Text)
    final_text = "\n".join(alive_configs)
    
    with open("wap_sub.txt", "w", encoding="utf-8") as f:
        f.write(final_text)
        
    print(">>> База успешно сохранена в wap_sub.txt (Plain Text)")

if __name__ == "__main__":
    process_configs()
