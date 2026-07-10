import requests
import re
import random
import base64

# --- 1. АГРЕГАТОРЫ ИСТОЧНИКОВ ---
URLS = [
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/base64/mix",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/refs/heads/main/subscriptions/v2ray/all_sub.txt",
    "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/share/vless",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/python/vless",
]

# --- 2. НАСТРОЙКИ ---
MAX_CONFIGS = 500 
ALLOWED_PORTS = ["443", "80", "8080", "8443", "2053", "2083", "2087", "2096", "11443"]

def decode_base64_robust(data):
    """Безопасный декодер Base64 с авто-восстановлением отступов"""
    data = data.strip()
    data += "=" * ((4 - len(data) % 4) % 4)
    try:
        return base64.b64decode(data).decode('utf-8', errors='ignore').splitlines()
    except Exception:
        return []

def process_configs():
    generated_configs = []
    print(f">>> Запуск сборки WAP-базы с сохранением ОРИГИНАЛЬНЫХ имен...")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200: continue
            
            content = resp.text.strip()
            
            # Распаковка если это Base64
            if "vless://" not in content[:50]:
                lines = decode_base64_robust(content)
            else:
                lines = content.splitlines()

            for line in lines:
                line = line.strip()
                
                # Защита от мусора и тяжелых строк
                if len(line) > 1000 or not line.startswith("vless://"): continue
                
                # Парсинг параметров
                match = re.search(r'@([^:]+):(\d+)\?([^#]+)', line)
                if not match: continue
                
                port = match.group(2)
                params = match.group(3)
                
                # ФИЛЬТР 1: Только WAP-совместимые порты
                if port not in ALLOWED_PORTS: continue
                
                # ФИЛЬТР 2: Только WAP-совместимый транспорт (без grpc/kcp)
                type_match = re.search(r'type=([^&]+)', params)
                transport = type_match.group(1) if type_match else "tcp"
                if transport not in ["tcp", "ws", "http"]: continue

                # Если конфиг прошел фильтры WAP, добавляем его КАК ЕСТЬ (первозданный вид)
                generated_configs.append(line)

        except Exception as e:
            print(f"[!] Ошибка с {url}: {e}")

    # Удаляем дубликаты
    unique_configs = list(set(generated_configs))
    print(f">>> Найдено чистых WAP VLESS: {len(unique_configs)}")

    # Перемешиваем и обрезаем до лимита
    random.shuffle(unique_configs)
    if len(unique_configs) > MAX_CONFIGS:
        unique_configs = unique_configs[:MAX_CONFIGS]

    # Упаковка в Base64 для безопасной передачи флагов стран
    final_text = "\n".join(unique_configs)
    final_base64 = base64.b64encode(final_text.encode('utf-8')).decode('utf-8')
    
    with open("wap_sub.txt", "w", encoding="utf-8") as f:
        f.write(final_base64)
        
    print(">>> База успешно скомпилирована в wap_sub.txt (Base64)")

if __name__ == "__main__":
    process_configs()
