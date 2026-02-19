import requests
import re
import random
import socket

# --- 1. ИСТОЧНИКИ (Обновляем) ---
URLS = [
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/liketolivefree/kobabi/refs/heads/main/sub.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/refs/heads/main/subscriptions/v2ray/all_sub.txt", # Хороший микс
]

# --- 2. СЛОВАРИ ДОМЕНОВ (Будут заполнены из твоего файла) ---
DOMAINS = {
    "YANDEX": [],
    "VK": [],
    "SBER": [],
    "GOV": [],
    "OTHER_RU": [] # Для остальных российских доменов (Ozon, Avito и т.д.)
}

# --- 3. ФУНКЦИИ ---
def categorize_domains(filename="good_sni.txt"):
    """Читает файл и сортирует домены по категориям."""
    print(f">>> Читаю и сортирую домены из {filename}...")
    try:
        with open(filename, 'r') as f:
            for line in f:
                domain = line.strip()
                if not domain or domain.startswith('#'): continue
                
                if any(x in domain for x in ['yandex', 'kinopoisk', 'ya.ru', 'dzen.ru', 'auto.ru']):
                    DOMAINS["YANDEX"].append(domain)
                elif any(x in domain for x in ['mail.ru', 'vk.com', 'ok.ru', 'userapi.com']):
                    DOMAINS["VK"].append(domain)
                elif 'sber' in domain:
                    DOMAINS["SBER"].append(domain)
                elif any(x in domain for x in ['gosuslugi', 'gov.ru']):
                    DOMAINS["GOV"].append(domain)
                else:
                    DOMAINS["OTHER_RU"].append(domain)
        print(">>> Сортировка доменов завершена.")
    except FileNotFoundError:
        print(f"!!! ОШИБКА: Файл {filename} не найден! SNI не будут заменены.")

def get_ip_provider(ip):
    # RU
    if re.match(r"^(51\.250|84\.201|158\.160|178\.154|130\.193|85\.193)\.", ip): return "YANDEX"
    if re.match(r"^(87\.240|95\.163|93\.186|217\.69|128\.140|185\.169)\.", ip): return "VK"
    if re.match(r"^(194\.54|185\.174)\.", ip): return "SBER"
    return "FOREIGN"

def verify_connection(ip, port, timeout=1.5):
    try:
        socket.create_connection((ip, int(port)), timeout=timeout)
        print(f"  [OK] Сервер {ip}:{port} жив.")
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        print(f"  [FAIL] Сервер {ip}:{port} мертв.")
        return False

def decode_if_needed(content):
    import base64
    if "vless://" in content or "vmess://" in content: return content.splitlines()
    try:
        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
        return decoded.splitlines()
    except: return []

def replace_sni(link, new_sni, tag):
    """Умная замена SNI и имени"""
    # Заменяем SNI
    link = re.sub(r'sni=[^&#]+', f'sni={new_sni}', link)
    # Заменяем Host (если есть, для WS)
    if "host=" in link:
        link = re.sub(r'host=[^&#]+', f'host={new_sni}', link)
    # Заменяем имя
    link = re.sub(r'#[^#]*$', f'#{tag}_{new_sni}', link)
    return link

def process_configs():
    categorize_domains() # <--- СНАЧАЛА ЗАГРУЖАЕМ ТВОИ ДОМЕНЫ
    verified_configs = []
    
    print(">>> Запускаю 'Умный траулер'...")
    for url in URLS:
        print(f"\n> Проверяю источник: {url[:50]}...")
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200: continue
            lines = decode_if_needed(resp.text.strip())

            for line in lines:
                line = line.strip()
                if not line.startswith("vless://") or "security=reality" not in line: continue
                
                match = re.search(r'@([^:]+):(\d+)', line)
                if not match: continue
                ip, port = match.group(1), match.group(2)
                
                if not verify_connection(ip, port): continue

                provider = get_ip_provider(ip)
                
                # --- ЛОГИКА ПОДБОРА SNI ---
                if provider == "FOREIGN":
                    # Для зарубежных просто оставляем как есть, меняя только имя
                    new_link = re.sub(r'#[^#]*$', '#🎯_Verified_DirectReality', line)
                    verified_configs.append(new_link)
                else: # Если сервер в РФ
                    # Выбираем правильный список доменов
                    domain_list = DOMAINS.get(provider, DOMAINS["OTHER_RU"])
                    if not domain_list: continue # Если для этого провайдера нет доменов
                    
                    # Размножаем конфиг с 2 разными SNI из твоего списка
                    selected_snis = random.sample(domain_list, min(2, len(domain_list)))
                    for sni in selected_snis:
                        new_link = replace_sni(line, sni, f"🇷🇺_Verified_{provider}")
                        verified_configs.append(new_link)

        except Exception as e:
            print(f"Ошибка с {url}: {e}")

    unique_configs = list(set(verified_configs))
    random.shuffle(unique_configs)
    
    print(f"\n>>> Готово! Свежий улов: {len(unique_configs)} проверенных и переименованных конфигов.")
    
    result_text = "\n".join(unique_configs)
    with open("final_whitelist_subs.txt", "w") as f:
        f.write(result_text)

if __name__ == "__main__":
    process_configs()
