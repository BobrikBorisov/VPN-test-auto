import requests
import re
import random
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 1. ИСТОЧНИКИ (Максимально широкая сеть) ---
URLS = [
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/liketolivefree/kobabi/refs/heads/main/sub.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/refs/heads/main/subscriptions/v2ray/all_sub.txt", # Хороший микс
]

# --- 2. СЛОВАРИ ДОМЕНОВ (Загружаются из файла) ---
DOMAINS = {"YANDEX": [], "VK": [], "SBER": [], "GOV": [], "OTHER_RU":[]}

# --- 3. ФУНКЦИИ ---
def categorize_domains(filename="good_sni.txt"):
    print(f">>> Читаю домены из {filename}...")
    try:
        with open(filename, 'r') as f:
            for line in f:
                domain = line.strip()
                if not domain or domain.startswith('#'): continue
                if any(x in domain for x in): DOMAINS.append(domain)
                elif any(x in domain for x in): DOMAINS.append(domain)
    except FileNotFoundError:
        print(f"!!! ВНИМАНИЕ: Файл {filename} не найден! RU-серверы не будут переименованы.")

def get_ip_provider(ip):
    if re.match(r"^(51\.250|84\.201|158\.160|178\.154|130\.193)\.", ip): return "YANDEX"
    if re.match(r"^(87\.240|95\.163|93\.186|217\.69|128\.140)\.", ip): return "VK"
    return "FOREIGN"

def is_server_stable(ip, port, timeout=1.0):
    """Двойная проверка стабильности сервера."""
    try:
        # Первая проверка
        socket.create_connection((ip, int(port)), timeout=timeout)
        # Пауза
        time.sleep(1)
        # Вторая проверка
        socket.create_connection((ip, int(port)), timeout=timeout)
        return True # Сервер стабилен, если прошел обе проверки
    except:
        return False

def decode_if_needed(content):
    import base64
    if "vless://" in content: return content.splitlines()
    try:
        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
        return decoded.splitlines()
    except: return[]

def verify_and_qualify(line):
    """Проверяет и квалифицирует один конфиг"""
    if not line.startswith("vless://") or "security=reality" not in line:
        return None, None
    
    match = re.search(r'@(+):(\d+)', line)
    if not match: return None, None
    
    ip, port = match.group(1), match.group(2)
    
    # --- Жесткий фильтр качества ---
    provider = get_ip_provider(ip)
    quality = 0
    if provider == "FOREIGN":
        if "flow=xtls-rprx-vision" in line:
            quality = 1 # Высший приоритет - Vision
        else:
            return None, None # <--- ОШИБКА БЫЛА ЗДЕСЬ (исправлено)
    else: # RU_YANDEX или RU_VK
        quality = 2 # Российские серверы тоже важны
        
    # --- Проверка стабильности ---
    if is_server_stable(ip, port):
        print(f" Найден стабильный сервер: {ip}:{port} (Тип: {provider})")
        return line, quality
        
    print(f" Сервер {ip}:{port} не прошел проверку стабильности.")
    return None, None

# --- ГЛАВНАЯ ЛОГИКА ---
def main():
    categorize_domains()
    candidate_configs =[]

    print(">>> Этап 1: Скачивание сырых данных...")
    for url in URLS:
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                candidate_configs.extend(decode_if_needed(resp.text.strip()))
        except Exception as e:
            print(f"Ошибка при скачивании {url}: {e}")
    
    unique_candidates = list(set(candidate_configs))
    print(f">>> Найдено {len(unique_candidates)} кандидатов. Начинаю проверку стабильности...")

    qualified_configs =[]
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_line = {executor.submit(verify_and_qualify, line): line for line in unique_candidates}
        for future in as_completed(future_to_line):
            try:
                result_line, quality = future.result()
                if result_line:
                    qualified_configs.append((result_line, quality))
            except Exception as e:
                # Защита: если отдельный поток упадет, скрипт продолжит работу
                pass
    
    print(f"\n>>> Этап 2: Проверка завершена. Найдено {len(qualified_configs)} стабильных серверов.")
    
    if not qualified_configs:
        print(">>> ОШИБКА: Не найдено ни одного стабильного сервера! Файл не обновлен.")
        return

    print(">>> Этап 3: Финальная обработка и переименование...")

    # Сортируем по качеству (Vision -> RU -> остальные)
    qualified_configs.sort(key=lambda x: x)

    final_configs =[]
    for line, quality in qualified_configs:
        match = re.search(r'@(+):', line)
        ip = match.group(1)
        provider = get_ip_provider(ip)
        
        if provider == "FOREIGN":
            new_link = re.sub(r'#*$', '#🎯_Stable_Vision', line)
            final_configs.append(new_link)
        else:
            domain_list = DOMAINS.get(provider)
            if domain_list:
                sni = random.choice(domain_list)
                new_link = re.sub(r'sni=+', f'sni={sni}', line)
                new_link = re.sub(r'#*$', f'#🇷🇺_Stable_{provider}_{sni}', new_link)
                final_configs.append(new_link)

    # Удаляем дубликаты (если они появились после замены SNI)
    unique_finals = list(set(final_configs))

    print(f"\n>>> Готово! Свежий и стабильный улов: {len(unique_finals)} конфигов.")
    
    result_text = "\n".join(unique_finals)
    with open("final_whitelist_subs.txt", "w") as f:
        f.write(result_text)

if __name__ == "__main__":
    main()
