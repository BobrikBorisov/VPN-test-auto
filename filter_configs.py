import requests
import re
import random

# --- 1. ИСТОЧНИКИ (Оптимизированный список) ---
# Убраны Epodonios и barry-far, так как они дают 90% мусора.
# Оставлены только качественные агрегаторы.
URLS = [
    # Качественные миксы
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/base64/mix",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/refs/heads/main/subscriptions/v2ray/all_sub.txt",
    
    # Специфические парсеры VLESS
    "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/share/vless",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/python/vless",
    
    # Элита Reality
    "https://raw.githubusercontent.com/NiREvil/vless/main/sub/vless_reality_tls_vision_tcp"
]

# --- НАСТРОЙКИ ---
MAX_CONFIGS = 1500 # Предел, после которого NekoBox не умрет
WHITELIST_DOMAINS = [
    "google.com", "microsoft.com", "update.microsoft.com", 
    "www.gstatic.com", "cdn.discordapp.com", "cdnjs.cloudflare.com"
]

# --- 3. IP-ДИАПАЗОНЫ ---
def get_ip_type(ip):
    # RU Segment
    if re.match(r"^(51\.250|84\.201|158\.160|178\.154|130\.193|85\.193|62\.119|213\.180)\.", ip): return "RU_YANDEX"
    if re.match(r"^(87\.240|95\.163|93\.186|217\.69|128\.140|185\.169)\.", ip): return "RU_VK"
    # Cloudflare CDN Ranges
    if re.match(r"^(104\.(1[6-9]|2[0-9]|31)|172\.(6[4-9]|7[0-1])|162\.159|198\.41)\.", ip): return "CDN_CLOUDFLARE"
    return "FOREIGN"

def replace_params(link, new_sni, new_name):
    # Меняем SNI и имя, сохраняя остальное
    if "sni=" in link: 
        link = re.sub(r'sni=[^&#]+', f'sni={new_sni}', link)
    else:
        link += f"&sni={new_sni}"
        
    # Удаляем старый хештег и ставим новый
    link = re.sub(r'#[^#]*$', f'#{new_name}', link)
    return link

def decode_if_needed(content):
    import base64
    if "vless://" in content: return content.splitlines()
    try:
        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
        return decoded.splitlines()
    except: return []

def process_configs():
    generated_configs = []
    print(f">>> Сбор мусора (Лимит: {MAX_CONFIGS})...")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200: continue
            
            lines = decode_if_needed(resp.text.strip())

            for line in lines:
                line = line.strip()
                # ФИЛЬТР 1: Только VLESS. VMess/Trojan выкидываем для экономии сил.
                if not line.startswith("vless://"): continue
                
                match = re.search(r'@([^:]+):', line)
                if not match: continue
                ip = match.group(1)
                
                ip_type = get_ip_type(ip)
                
                # --- ЛОГИКА ОБРАБОТКИ ---
                
                if ip_type.startswith("RU_"):
                    # Российские берем всегда
                    generated_configs.append(line.replace("#", f"#🇷🇺_{ip_type}_"))
                
                elif ip_type == "CDN_CLOUDFLARE" and "ws" in line:
                    # CDN берем, но БЕЗ РАЗМНОЖЕНИЯ. 1 конфиг = 1 вариант.
                    # Берем рандомный белый домен
                    sni = random.choice(WHITELIST_DOMAINS)
                    new_name = f"☁️_CDN_Mix"
                    new_link = replace_params(line, sni, new_name)
                    generated_configs.append(new_link)

                elif ip_type == "FOREIGN":
                    # Остальные иностранные. Берем только Reality.
                    if "security=reality" in line:
                        generated_configs.append(line.replace("#", "#🎯_Reality_Mix"))

        except Exception as e:
            print(f"Ошибка с {url}: {e}")

    # Удаляем дубликаты
    unique_configs = list(set(generated_configs))
    print(f">>> Найдено уникальных VLESS: {len(unique_configs)}")

    # ПЕРЕМЕШИВАЕМ И ОБРЕЗАЕМ
    # Это самое важное. Мы берем случайную выборку, чтобы не потерять разнообразие.
    random.shuffle(unique_configs)
    
    if len(unique_configs) > MAX_CONFIGS:
        unique_configs = unique_configs[:MAX_CONFIGS]
        print(f">>> Обрезано до {MAX_CONFIGS} штук.")
    
    result_text = "\n".join(unique_configs)
    
    with open("final_whitelist_subs.txt", "w") as f:
        f.write(result_text)

if __name__ == "__main__":
    process_configs()
