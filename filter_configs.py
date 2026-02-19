import requests
import re
import random
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 1. ИСТОЧНИКИ ---
URLS = [
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/liketolivefree/kobabi/refs/heads/main/sub.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/refs/heads/main/subscriptions/v2ray/all_sub.txt"
]

# --- 2. СЛОВАРИ ДОМЕНОВ ---
DOMAINS = {"YANDEX": [], "VK": [], "SBER": [], "GOV": [], "OTHER_RU": []}

# --- 3. ФУНКЦИИ ---
def categorize_domains(filename="good_sni.txt"):
    print(f">>> Читаю домены из {filename}...")
    try:
        with open(filename, 'r') as f:
            for line in f:
                domain = line.strip()
                if not domain or domain.startswith('#'): continue
                
                # Исправленная логика списков
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
    except FileNotFoundError:
        print(f"!!! ВНИМАНИЕ: Файл {filename} не найден! RU-серверы не будут переименованы.")

def get_ip_provider(ip):
    # Диапазоны Яндекса
    if re.match(r"^(51\.250|84\.201|158\.160|178\.154|130\.193|85\.193|62\.119|213\.180)\.", ip): return "YANDEX"
    # Диапазоны VK/Mail
    if re.match(r"^(87\.240|95\.163|93\.186|217\.69|128\.140|185\.169)\.", ip): return "VK"
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
        return True 
    except:
        return False

def decode_if_needed(content):
    import base64
    if "vless://" in content: return content.splitlines()
    try:
        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
        return decoded.splitlines()
    except: return []

def verify_and_qualify(line):
    """Проверяет и квалифицирует один конфиг"""
    line = line.strip()
    if not line.startswith("vless://") or "security=reality" not in line:
        return None, None
    
    # Исправленное регулярное выражение для поиска IP и порта
    match = re.search(r'@([^:]+):(\d+)', line)
    if not match: return None, None
    
    ip, port = match.group(1), match.group(2)
    
    # --- Жесткий фильтр качества ---
    provider = get_ip_provider(ip)
    quality = 0
    
    if provider == "FOREIGN":
        if "flow=xtls-rprx-vision" in line:
            quality = 1 # Высший приоритет - Vision
        else:
            return None, None # Отбрасываем зарубежные без Vision
    else: 
        quality = 2 # Российские серверы (Yandex/VK)
        
    # --- Проверка стабильности ---
    if is_server_stable(ip, port):
        return line, quality
        
    return None, None

# --- ГЛАВНАЯ ЛОГИКА ---
def main():
    categorize_domains()
    candidate_configs = []

    print(">>> Этап 1: Скачивание сырых данных...")
    for url in URLS:
        try:
            print(f"Скачиваю: {url}...")
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                candidate_configs.extend(decode_if_needed(resp.text.strip()))
        except Exception as e:
            print(f"Ошибка при скачивании {url}: {e}")
    
    unique_candidates = list(set(candidate_configs))
    print(f">>> Найдено {len(unique_candidates)} уникальных кандидатов. Начинаю проверку стабильности...")

    qualified_configs = []
    # Запускаем 50 потоков для проверки
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_line = {executor.submit(verify_and_qualify, line): line for line in unique_candidates}
        for future in as_completed(future_to_line):
            try:
                result_line, quality = future.result()
                if result_line:
                    qualified_configs.append((result_line, quality))
            except Exception:
                pass
    
    print(f"\n>>> Этап 2: Проверка завершена. Найдено {len(qualified_configs)} стабильных серверов.")
    
    if not qualified_configs:
        print(">>> ОШИБКА: Не найдено ни одного стабильного сервера! Файл не обновлен.")
        # Создаем пустой файл или выходим, чтобы не ломать пайплайн
        with open("final_whitelist_subs.txt", "w") as f:
            f.write("")
        return

    print(">>> Этап 3: Финальная обработка и переименование...")

    # Сортируем по качеству (Vision -> RU -> остальные)
    qualified_configs.sort(key=lambda x: x[1])

    final_configs = []
    for line, quality in qualified_configs:
        match = re.search(r'@([^:]+):', line)
        if not match: continue
        ip = match.group(1)
        provider = get_ip_provider(ip)
        
        if provider == "FOREIGN":
            # Исправленный regex для замены имени
            new_link = re.sub(r'#[^#]*$', '#🎯_Stable_Vision', line)
            final_configs.append(new_link)
        else:
            domain_list = DOMAINS.get(provider, DOMAINS["OTHER_RU"])
            if domain_list:
                sni = random.choice(domain_list)
                # Исправленные regex для замены SNI и имени
                new_link = re.sub(r'sni=[^&#]+', f'sni={sni}', line)
                new_link = re.sub(r'#[^#]*$', f'#🇷🇺_Stable_{provider}_{sni}', new_link)
                final_configs.append(new_link)

    # Удаляем дубликаты
    unique_finals = list(set(final_configs))

    print(f"\n>>> Готово! Свежий и стабильный улов: {len(unique_finals)} конфигов.")
    
    result_text = "\n".join(unique_finals)
    with open("final_whitelist_subs.txt", "w") as f:
        f.write(result_text)

if __name__ == "__main__":
    main()
