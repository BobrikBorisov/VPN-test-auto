import requests
import base64
import re
import random
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# --- 1. ТВОИ ИСТОЧНИКИ ---
URLS = [
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt",
  "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_Sub.txt",
"https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_base64_Sub.txt",
]

# --- 2. ТВОИ ДОМЕНЫ (ОТСОРТИРОВАННЫЕ ИЗ ТВОЕГО ФАЙЛА) ---
# Группа Яндекс (IP 51.250, 84.201, 158.160, 178.154, 130.193)
DOMAINS_YANDEX = [
    "travel.yandex.ru", "kinopoisk.ru", "hd.kinopoisk.ru", "mobile.yandex.ru",
    "music.yandex.ru", "yandex.ru", "dzen.ru", "ya.ru", "mail.yandex.ru",
    "disk.yandex.ru", "auto.ru", "market.yandex.ru", "taxi.yandex.ru",
    "payment-widget.plus.kinopoisk.ru", "st.kinopoisk.ru", "api.plus.kinopoisk.ru"
]

# Группа VK / Mail.ru (IP 95.163, 87.240, 93.186 + Selectel иногда)
DOMAINS_VK = [
    "vk.com", "m.vk.com", "api.vk.com", "login.vk.com", "mail.ru", "cloud.mail.ru",
    "e.mail.ru", "ok.ru", "m.ok.ru", "userapi.com", "sun9-101.userapi.com",
    "vkuser.net", "vk-portal.net", "imgs.mail.ru", "otvet.mail.ru"
]

# Группа Сбер (IP 194.54, 185.174)
DOMAINS_SBER = [
    "sberbank.ru", "online.sberbank.ru", "id.sber.ru", "api.sberbank.ru"
]

# Группа Гос / Нейтральные (Если провайдер не определен, пробуем эти)
DOMAINS_GOV = [
    "gosuslugi.ru", "lk.gosuslugi.ru", "esia.gosuslugi.ru", "nalog.ru", "mos.ru"
]

# --- 3. ДИАПАЗОНЫ IP (ОПРЕДЕЛИТЕЛЬ ПРОВАЙДЕРА) ---
# Это упрощенная проверка по первым октетам
def detect_provider(ip):
    if re.match(r"^(51\.250|84\.201|158\.160|178\.154|130\.193|85\.193|62\.119|213\.180)\.", ip):
        return "YANDEX"
    if re.match(r"^(87\.240|95\.163|93\.186|217\.69|128\.140|185\.169)\.", ip):
        return "VK"
    if re.match(r"^(194\.54|185\.174)\.", ip):
        return "SBER"
    return "UNKNOWN"

# --- ФУНКЦИИ ---
def decode_base64(data):
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    try:
        return base64.b64decode(data).decode('utf-8', errors='ignore')
    except:
        return ""

def parse_vless(link):
    """Разбирает ссылку vless:// на части"""
    try:
        # Убираем vless://
        body = link[8:]
        if "@" not in body: return None # Нестандартная ссылка
        
        uuid_part, rest = body.split("@", 1)
        if ":" not in rest: return None
        
        ip_port, params_raw = rest.split("?", 1)
        ip, port = ip_port.split(":", 1)
        
        if "#" in params_raw:
            query_str, name = params_raw.split("#", 1)
        else:
            query_str, name = params_raw, "NoName"
            
        params = parse_qs(query_str)
        return {"uuid": uuid_part, "ip": ip, "port": port, "params": params, "name": name}
    except:
        return None

def build_vless(data, new_sni, tag_suffix):
    """Собирает ссылку обратно с новым SNI"""
    # Обновляем SNI в параметрах
    data['params']['sni'] = [new_sni]
    
    # Можно также обновить host, если он есть (для WS)
    if 'host' in data['params']:
         data['params']['host'] = [new_sni]

    # Собираем строку параметров
    query_string = urlencode(data['params'], doseq=True)
    
    # Новое имя
    new_name = f"{data['name']}_{tag_suffix}"
    
    return f"vless://{data['uuid']}@{data['ip']}:{data['port']}?{query_string}#{new_name}"

def process_configs():
    generated_configs = []
    
    print(">>> Скачивание и анализ...")
    
    for url in URLS:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200: continue
            
            content = resp.text.strip()
            # Пробуем декодировать Base64, если это не чистый текст
            if "vless://" not in content:
                 decoded = decode_base64(content)
                 lines = decoded.splitlines()
            else:
                 lines = content.splitlines()

            for line in lines:
                line = line.strip()
                if not line.startswith("vless://"): continue
                
                # Парсим конфиг
                config = parse_vless(line)
                if not config: continue
                
                ip = config['ip']
                provider = detect_provider(ip)
                
                # Фильтр: берем только RU IP (если провайдер определился или IP похож на RU)
                # Можно расширить регулярки выше, но пока берем только точное совпадение
                if provider == "UNKNOWN":
                    # Дополнительная проверка: пропускать совсем левые IP
                    continue 

                # Выбираем список доменов
                target_domains = []
                if provider == "YANDEX":
                    target_domains = DOMAINS_YANDEX
                elif provider == "VK":
                    target_domains = DOMAINS_VK
                elif provider == "SBER":
                    target_domains = DOMAINS_SBER
                
                # ГЕНЕРАЦИЯ ВАРИАНТОВ
                # Берем исходный конфиг и создаем 3 копии с РАЗНЫМИ доменами из списка
                # Чтобы не раздувать файл до гигабайта, берем 3 случайных домена
                selected_snis = random.sample(target_domains, min(3, len(target_domains)))
                
                for i, sni in enumerate(selected_snis):
                    # Пропускаем, если домен уже такой же
                    current_sni = config['params'].get('sni', [''])[0]
                    if current_sni == sni:
                        generated_configs.append(line) # Оставляем оригинал
                        continue
                        
                    new_link = build_vless(config, sni, f"{provider}_{i+1}")
                    generated_configs.append(new_link)

        except Exception as e:
            print(f"Error {url}: {e}")

    # Удаляем дубликаты
    unique_configs = list(set(generated_configs))
    print(f">>> Готово! Сгенерировано {len(unique_configs)} конфигов.")
    
    # Кодируем в Base64
    result_text = "\n".join(unique_configs)
    result_base64 = base64.b64encode(result_text.encode('utf-8')).decode('utf-8')
    
    with open("final_whitelist_subs.txt", "w") as f:
        f.write(result_base64)

if __name__ == "__main__":
    process_configs()
