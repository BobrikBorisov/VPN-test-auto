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
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/refs/heads/main/subscriptions/v2ray/all_sub.txt", # Хороший микс
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
        print(f"!!! Файл {filename} не найден.")

def get_ip_provider(ip):
    if re.match(r"^(51\.250|84\.201|158\.160|178\.154|130\.193|85\.193|62\.119|213\.180)\.", ip): return "YANDEX"
    if re.match(r"^(87\.240|95\.163|93\.186|217\.69|128\.140|185\.169)\.", ip): return "VK"
    return "FOREIGN"

def check_latency(ip, port, timeout=0.8):
    """Замеряет задержку. Возвращает ms или None, если мертв."""
    try:
        start = time.time()
        sock = socket.create_connection((ip, int(port)), timeout=timeout)
        sock.close()
        end = time.time()
        return (end - start) * 1000 # Переводим в миллисекунды
    except:
        return None

def decode_if_needed(content):
    import base64
    if "vless://" in content: return content.splitlines()
    try:
        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
        return decoded.splitlines()
    except: return []

def process_single(line):
    """Анализ одного конфига"""
    line = line.strip()
    if not line.startswith("vless://") or "security=reality" not in line:
        return None
    
    match = re.search(r'@([^:]+):(\d+)', line)
    if not match: return None
    
    ip, port = match.group(1), match.group(2)
    provider = get_ip_provider(ip)
    
    # 1. Фильтр протокола для иностранцев
    if provider == "FOREIGN" and "flow=xtls-rprx-vision" not in line:
        return None

    # 2. Проверка скорости
    latency = check_latency(ip, port)
    if latency is None:
        return None
    
    # Бонус за порт 443 (он меньше блокируется)
    score = latency
    if port != "443":
        score += 200 # Штраф 200мс за нестандартный порт
        
    return {
        "line": line,
        "provider": provider,
        "score": score, # Чем меньше, тем лучше
        "sni_list": DOMAINS.get(provider, DOMAINS["OTHER_RU"])
    }

# --- ГЛАВНАЯ ЛОГИКА ---
def main():
    categorize_domains()
    raw_candidates = []

    print(">>> Этап 1: Сбор данных...")
    for url in URLS:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                raw_candidates.extend(decode_if_needed(resp.text.strip()))
        except: pass
    
    unique_candidates = list(set(raw_candidates))
    print(f">>> Кандидатов: {len(unique_candidates)}. Фильтрация по скорости...")

    good_foreign = []
    good_ru = []

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(process_single, line) for line in unique_candidates]
        for future in as_completed(futures):
            res = future.result()
            if res:
                if res["provider"] == "FOREIGN":
                    good_foreign.append(res)
                else:
                    good_ru.append(res)

    # Сортируем по скорости (от быстрых к медленным)
    good_foreign.sort(key=lambda x: x["score"])
    good_ru.sort(key=lambda x: x["score"])

    # --- ЖЕСТКИЙ ОТБОР ТОП-ОВ ---
    # Берем только 30 лучших иностранных и 30 лучших русских
    top_foreign = good_foreign[:30]
    top_ru = good_ru[:30]
    
    print(f"\n>>> Итог: RU={len(top_ru)}, FOREIGN={len(top_foreign)}")

    final_lines = []

    # Обработка FOREIGN
    for item in top_foreign:
        line = item["line"]
        new_link = re.sub(r'#[^#]*$', f'#🎯_Fast_{int(item["score"])}ms', line)
        final_lines.append(new_link)

    # Обработка RU
    for item in top_ru:
        line = item["line"]
        sni_list = item["sni_list"]
        if sni_list:
            # Делаем 2 варианта SNI для каждого хорошего сервера
            snis = random.sample(sni_list, min(2, len(sni_list)))
            for sni in snis:
                l = re.sub(r'sni=[^&#]+', f'sni={sni}', line)
                l = re.sub(r'#[^#]*$', f'#🇷🇺_{item["provider"]}_{sni}', l)
                final_lines.append(l)

    # Перемешиваем, чтобы не шли подряд
    random.shuffle(final_lines)

    result_text = "\n".join(final_lines)
    with open("final_whitelist_subs.txt", "w") as f:
        f.write(result_text)
    
    print(f">>> Сохранено {len(final_lines)} лучших конфигов.")

if __name__ == "__main__":
    main()
