import requests
import re
import random

# --- 1. ИСТОЧНИКИ (Добавил побольше универсальных) ---
URLS = [
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/liketolivefree/kobabi/refs/heads/main/sub.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/refs/heads/main/subscriptions/v2ray/all_sub.txt", # Хороший микс
]

# --- 2. ДОМЕНЫ ДЛЯ ПОДМЕНЫ В CDN-КОНФИГАХ ---
WHITELIST_DOMAINS = [
    "travel.yandex.ru", "kinopoisk.ru", "hd.kinopoisk.ru", "music.yandex.ru",
    "dzen.ru", "ya.ru", "vk.com", "m.vk.com", "api.vk.com", "mail.ru", "cloud.mail.ru",
    "ok.ru", "gosuslugi.ru", "sberbank.ru", "auto.ru", "ozon.ru"
]

# --- 3. IP-ДИАПАЗОНЫ ---
def get_ip_type(ip):
    # Yandex Cloud (RU)
    if re.match(r"^(51\.250|84\.201|158\.160|178\.154|130\.193|85\.193|62\.119|213\.180)\.", ip):
        return "RU_YANDEX"
    # VK Cloud / Mail.ru (RU)
    if re.match(r"^(87\.240|95\.163|93\.186|217\.69|128\.140|185\.169)\.", ip):
        return "RU_VK"
    # Cloudflare (CDN) - самые важные для мобильных
    if re.match(r"^(104\.(1[6-9]|2[0-9]|31)|172\.(6[4-9]|7[0-1])|162\.159|198\.41)\.", ip):
        return "CDN_CLOUDFLARE"
    return "FOREIGN" # Другой зарубежный

# --- ФУНКЦИИ ---
def replace_params(link, new_sni, new_name):
    # Меняем SNI, Host и Name
    link = re.sub(r'sni=[^&#]+', f'sni={new_sni}', link)
    link = re.sub(r'host=[^&#]+', f'host={new_sni}', link)
    if "#" in link:
        link = re.sub(r'#[^#]*$', f'#{new_name}', link)
    else:
        link += f"#{new_name}"
    return link

def decode_if_needed(content):
    import base64
    if "vless://" in content or "vmess://" in content:
        return content.splitlines()
    try:
        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
        return decoded.splitlines()
    except:
        return []

def process_configs():
    generated_configs = []
    print(">>> Начинаю обработку по новой стратегии...")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200: continue
            
            lines = decode_if_needed(resp.text.strip())

            for line in lines:
                line = line.strip()
                if not (line.startswith("vless://") or line.startswith("vmess://")): continue
                
                # Ищем IP (работает и для vmess, и для vless)
                match = re.search(r'@([^:]+):', line) or re.search(r'"add":"([^"]+)"', line)
                if not match: continue
                ip = match.group(1)
                
                ip_type = get_ip_type(ip)
                
                # --- ЛОГИКА ФИЛЬТРАЦИИ ---
                
                # 1. Если это RU-сервер (хорошо для Wi-Fi)
                if ip_type.startswith("RU_"):
                    # Оставляем как есть, автор подписки zieng2 уже все настроил
                    generated_configs.append(line.replace("#", f"#🇷🇺_{ip_type}_"))
                
                # 2. Если это Cloudflare (наша надежда для моб. интернета)
                elif ip_type == "CDN_CLOUDFLARE" and "ws" in line:
                    # Размножаем конфиг с разными "белыми" SNI
                    for _ in range(2): # Делаем 2 варианта
                        sni = random.choice(WHITELIST_DOMAINS)
                        new_name = f"☁️_CDN_{sni}"
                        new_link = replace_params(line, sni, new_name)
                        generated_configs.append(new_link)

                # 3. Если это прямой зарубежный VLESS+Reality (Снайпер)
                elif ip_type == "FOREIGN" and "security=reality" in line:
                    # Оставляем как есть, не меняем SNI!
                    generated_configs.append(line.replace("#", "#🎯_DirectReality_"))

        except Exception as e:
            print(f"Ошибка с {url}: {e}")

    unique_configs = list(set(generated_configs))
    random.shuffle(unique_configs)
    
    print(f">>> Готово! Найдено {len(unique_configs)} потенциально рабочих конфигов.")
    
    result_text = "\n".join(unique_configs)
    
    with open("final_whitelist_subs.txt", "w") as f:
        f.write(result_text)

if __name__ == "__main__":
    process_configs()
