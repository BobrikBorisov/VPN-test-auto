import requests
import re
import random
import base64

# === 1. АГРЕГАТОРЫ ИСТОЧНИКОВ ===
URLS = [
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/refs/heads/main/subscriptions/v2ray/all_sub.txt",
    "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/share/vless",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/python/vless",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/vless.txt"
]

# === 2. НАСТРОЙКИ ФИЛЬТРАЦИИ ===
MAX_CONFIGS = 500 
# Убиваем Иран, Китай и Гонконг
BLACKLIST_WORDS = ["CN", "IR", "HK", "CHINA", "IRAN", "ИРАН", "КИТАЙ", "🇮🇷", "🇨🇳", "🇭🇰"]
# WAP не пропускает эти виды транспорта
FORBIDDEN_TRANSPORTS = ["kcp", "quic", "grpc"]

def decode_base64_robust(data):
    data = data.strip()
    data += "=" * ((4 - len(data) % 4) % 4)
    try:
        return base64.b64decode(data).decode('utf-8', errors='ignore').splitlines()
    except Exception:
        return []

def process_configs():
    parsed_data = []
    print(">>> ИНИЦИАЛИЗАЦИЯ WAP-САНИТАЙЗЕРА (БЕЗ ОБЛАЧНОГО ПРОЗВОНА) <<<")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200: continue
            
            content = resp.text.strip()
            lines = content.splitlines() if "vless://" in content[:50] else decode_base64_robust(content)

            for line in lines:
                line = line.strip()
                if len(line) > 1000 or not line.startswith("vless://"): continue
                
                # Парсинг имени и параметров
                match = re.search(r'@([^:]+):(\d+)\?([^#]+)#?(.*)', line)
                if not match: 
                    match = re.search(r'@([^:]+):(\d+)\?([^#]+)', line)
                    if not match: continue
                    remark = ""
                else:
                    remark = match.group(4).upper()

                # ГЕО-ФИЛЬТР (Черный список стран)
                if any(bad in remark for bad in BLACKLIST_WORDS): continue
                
                params = match.group(3)
                
                # ФИЛЬТР ТРАНСПОРТА (Только TCP/WS для WAP)
                type_match = re.search(r'type=([^&]+)', params)
                transport = type_match.group(1) if type_match else "tcp"
                if transport in FORBIDDEN_TRANSPORTS: continue

                parsed_data.append(line)

        except Exception as e:
            print(f"[!] Ошибка с источником {url}: {e}")

    # Удаляем дубликаты
    unique_configs = list(set(parsed_data))
    print(f"\n[+] Собрано чистых уникальных серверов: {len(unique_configs)}")

    if not unique_configs:
        print("[!] База пуста. Сборка остановлена.")
        return

    # Перемешиваем и ограничиваем до 500 штук
    random.shuffle(unique_configs)
    if len(unique_configs) > MAX_CONFIGS:
        unique_configs = unique_configs[:MAX_CONFIGS]

    # Сохраняем как обычный текст
    final_text = "\n".join(unique_configs)
    
    with open("wap_sub.txt", "w", encoding="utf-8") as f:
        f.write(final_text)
        
    print(f">>> База из {len(unique_configs)} серверов успешно сохранена (wap_sub.txt)")

if __name__ == "__main__":
    process_configs()
