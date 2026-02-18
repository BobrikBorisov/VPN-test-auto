import requests
import re
import random

# --- 1. ИСТОЧНИКИ ---
URLS = [
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt",
]

# --- 2. ДОМЕНЫ ДЛЯ ПОДМЕНЫ ---
DOMAINS_YANDEX = [
    "travel.yandex.ru", "kinopoisk.ru", "hd.kinopoisk.ru", "mobile.yandex.ru",
    "music.yandex.ru", "yandex.ru", "dzen.ru", "ya.ru", "disk.yandex.ru", 
    "auto.ru", "market.yandex.ru", "taxi.yandex.ru"
]
DOMAINS_VK = [
    "vk.com", "m.vk.com", "api.vk.com", "login.vk.com", "mail.ru", "cloud.mail.ru",
    "e.mail.ru", "ok.ru", "userapi.com", "vkuser.net", "vk-portal.net"
]
DOMAINS_SBER = ["sberbank.ru", "online.sberbank.ru", "id.sber.ru"]
DOMAINS_GOV = ["gosuslugi.ru", "lk.gosuslugi.ru", "nalog.ru", "mos.ru"]

# --- 3. ФУНКЦИИ ---
def get_provider(ip):
    """Определяет провайдера по IP"""
    if re.match(r"^(51\.250|84\.201|158\.160|178\.154|130\.193|85\.193|62\.119|213\.180)\.", ip):
        return "YANDEX", DOMAINS_YANDEX
    if re.match(r"^(87\.240|95\.163|93\.186|217\.69|128\.140|185\.169)\.", ip):
        return "VK", DOMAINS_VK
    if re.match(r"^(194\.54|185\.174)\.", ip):
        return "SBER", DOMAINS_SBER
    return "UNKNOWN", DOMAINS_GOV

def replace_sni(link, new_sni, new_name):
    """Меняет SNI и название в ссылке через Regex"""
    # 1. Заменяем или добавляем SNI
    if "sni=" in link:
        link = re.sub(r'sni=[^&#]+', f'sni={new_sni}', link)
    else:
        # Если sni нет, добавляем его перед хештегом # или в конец
        if "#" in link:
            link = link.replace("#", f"&sni={new_sni}#", 1)
        else:
            link += f"&sni={new_sni}"
            
    # 2. Также меняем host, если он есть (для надежности)
    if "host=" in link:
        link = re.sub(r'host=[^&#]+', f'host={new_sni}', link)

    # 3. Меняем название (хештег в конце)
    if "#" in link:
        link = re.sub(r'#[^#]*$', f'#{new_name}', link)
    else:
        link += f"#{new_name}"
        
    return link

def decode_if_needed(content):
    """Пытается найти ссылки, если файл зашифрован"""
    import base64
    if "vless://" in content:
        return content.splitlines()
    try:
        # Пытаемся декодировать Base64
        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
        return decoded.splitlines()
    except:
        return []

def process_configs():
    generated_configs = []
    print(">>> Начинаю обработку...")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200: continue
            
            lines = decode_if_needed(resp.text.strip())

            for line in lines:
                line = line.strip()
                if not line.startswith("vless://"): continue
                
                # Ищем IP адрес в ссылке (между @ и :)
                match = re.search(r'@([^:]+):', line)
                if not match: continue
                ip = match.group(1)
                
                provider_name, domain_list = get_provider(ip)
                
                # Если это не целевой провайдер - пропускаем
                if provider_name == "UNKNOWN": continue

                # Генерируем 2 варианта для надежности
                selected_snis = random.sample(domain_list, min(2, len(domain_list)))
                
                for i, sni in enumerate(selected_snis):
                    new_link = replace_sni(line, sni, f"🇷🇺_{provider_name}_{i+1}_{sni}")
                    generated_configs.append(new_link)

        except Exception as e:
            print(f"Ошибка с {url}: {e}")

    # Удаляем дубликаты и перемешиваем
    unique_configs = list(set(generated_configs))
    random.shuffle(unique_configs)
    
    print(f">>> Найдено: {len(unique_configs)} конфигов.")
    
    # Сохраняем ПРОСТЫМ ТЕКСТОМ (без Base64)
    result_text = "\n".join(unique_configs)
    
    with open("final_whitelist_subs.txt", "w") as f:
        f.write(result_text)

if __name__ == "__main__":
    process_configs()
        f.write(result_base64)

if __name__ == "__main__":
    process_configs()
