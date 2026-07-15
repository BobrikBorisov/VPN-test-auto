import requests
import re
import random
import base64
import asyncio

# --- 1. АГРЕГАТОРЫ ИСТОЧНИКОВ ---
URLS = [
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/base64/mix",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/refs/heads/main/subscriptions/v2ray/all_sub.txt",
    "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/share/vless",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/python/vless",
]

# --- 2. НАСТРОЙКИ ---
MAX_CONFIGS = 300 
ALLOWED_PORTS = ["443", "80", "8080", "8443", "2053", "2083", "2087", "2096", "11443"]

def decode_base64_robust(data):
    data = data.strip()
    data += "=" * ((4 - len(data) % 4) % 4)
    try:
        return base64.b64decode(data).decode('utf-8', errors='ignore').splitlines()
    except Exception:
        return []

# --- 3. АСИНХРОННЫЙ СЕМАФОР (АППАРАТНЫЙ ДРОССЕЛЬ) ---
# Ограничиваем шторм запросов до 50 одновременных сокетов, чтобы ядро GitHub не упало
sem = asyncio.Semaphore(50)

async def check_port(ip, port, config_line):
    async with sem:
        try:
            # Пытаемся открыть TCP-соединение с таймаутом 3 секунды
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, int(port)), timeout=3.0
            )
            writer.close()
            await writer.wait_closed()
            return config_line
        except Exception:
            return None

async def verify_configs(parsed_configs):
    print(f">>> Начинаем TCP-прозвон {len(parsed_configs)} серверов (потоками по 50 штук)...")
    tasks = [check_port(ip, port, config) for config, ip, port in parsed_configs]
    
    results = await asyncio.gather(*tasks)
    alive_configs = [res for res in results if res is not None]
    return alive_configs

def process_configs():
    parsed_data = []
    print(">>> Запуск парсера WAP-совместимой базы...")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200: continue
            
            content = resp.text.strip()
            lines = content.splitlines() if "vless://" in content[:50] else decode_base64_robust(content)

            for line in lines:
                line = line.strip()
                if len(line) > 1000 or not line.startswith("vless://"): continue
                
                match = re.search(r'@([^:]+):(\d+)\?([^#]+)', line)
                if not match: continue
                
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
    
    # Запускаем аккуратный прозвон
    alive_configs = asyncio.run(verify_configs(parsed_data))
    print(f">>> Выжило после прозвона: {len(alive_configs)} узлов")

    if len(alive_configs) == 0:
        print("[!] ОШИБКА: Выживших серверов нет. База пуста.")
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
