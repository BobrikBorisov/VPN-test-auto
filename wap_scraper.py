import requests
import re
import random
import base64

# --- 1. АГРЕГАТОРЫ ИСТОЧНИКОВ (Можно добавлять любые) ---
URLS = [
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/base64/mix",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/refs/heads/main/subscriptions/v2ray/all_sub.txt",
    "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/share/vless",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/python/vless",
]

# --- 2. ЖЕСТКИЕ ПАРАМЕТРЫ ДЛЯ WAP-СЕТИ МТС ---
MAX_CONFIGS = 500 
ALLOWED_PORTS = ["443", "80", "8080", "8443", "2053", "2083", "2087", "2096", "11443"]
WHITELIST_DOMAINS = ["google.com", "microsoft.com", "update.microsoft.com", "www.gstatic.com", "cdn.discordapp.com"]

def get_ip_type(ip):
    if re.match(r"^(51\.250|84\.201|158\.160|178\.154|130\.193|85\.193|62\.119|213\.180)\.", ip): return "RU_YANDEX"
    if re.match(r"^(87\.240|95\.163|93\.186|217\.69|128\.140|185\.169)\.", ip): return "RU_VK"
    if re.match(r"^(104\.(1[6-9]|2[0-9]|31)|172\.(6[4-9]|7[0-1])|162\.159|198\.41)\.", ip): return "CDN_CLOUDFLARE"
    return "FOREIGN"

def replace_params(link, new_sni, new_name):
    if "sni=" in link: 
        link = re.sub(r'sni=[^&#]+', f'sni={new_sni}', link)
    else:
        link += f"&sni={new_sni}"
    link = re.sub(r'#[^#]*$', f'#{new_name}', link)
    return link

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
    print(f">>> Запуск сборки WAP-совместимой базы (Лимит: {MAX_CONFIGS})...")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200: continue
            
            content = resp.text.strip()
            # Проверяем, зашифрован ли файл
            if "vless://" not in content[:50]:
                lines = decode_base64_robust(content)
            else:
                lines = content.splitlines()

            for line in lines:
                line = line.strip()
                
                # Базовый фильтр
                if len(line) > 1000 or "%25" in line or not line.startswith("vless://"): continue
                
                # --- АНАЛИЗАТОР WAP-СОВМЕСТИМОСТИ ---
                # Вытаскиваем IP, Порт и Параметры
                match = re.search(r'@([^:]+):(\d+)\?([^#]+)', line)
                if not match: continue
                
                ip = match.group(1)
                port = match.group(2)
                params = match.group(3)
                
                # 1. Фильтр по разрешенным HTTP/HTTPS портам
                if port not in ALLOWED_PORTS: continue
                
                # 2. Фильтр по транспорту (Вырезаем grpc, kcp, quic)
                type_match = re.search(r'type=([^&]+)', params)
                transport = type_match.group(1) if type_match else "tcp"
                if transport not in ["tcp", "ws", "http"]: continue

                ip_type = get_ip_type(ip)
                
                # Присвоение тегов
                if ip_type.startswith("RU_"):
                    generated_configs.append(line.replace("#", f"#🇷🇺_WAP_{ip_type}_"))
                elif ip_type == "CDN_CLOUDFLARE" and transport == "ws":
                    sni = random.choice(WHITELIST_DOMAINS)
                    new_link = replace_params(line, sni, "☁️_WAP_CDN_Mix")
                    generated_configs.append(new_link)
                elif ip_type == "FOREIGN":
                    if "security=reality" in line:
                        generated_configs.append(line.replace("#", "#🎯_WAP_Reality"))

        except Exception as e:
            print(f"[!] Ошибка с {url}: {e}")

    # Удаляем дубликаты
    unique_configs = list(set(generated_configs))
    print(f">>> Найдено WAP-совместимых VLESS: {len(unique_configs)}")

    random.shuffle(unique_configs)
    if len(unique_configs) > MAX_CONFIGS:
        unique_configs = unique_configs[:MAX_CONFIGS]
    
    # Karing и NekoBox требуют Base64 для надежного импорта
    final_text = "\n".join(unique_configs)
    final_base64 = base64.b64encode(final_text.encode('utf-8')).decode('utf-8')
    
    with open("wap_sub.txt", "w") as f:
        f.write(final_base64)
        
    print(f">>> База успешно скомпилирована в wap_sub.txt")

if __name__ == "__main__":
    process_configs()
