from requests import post
from random import sample
from string import ascii_letters, digits
from poplib import POP3_SSL
from email import message_from_bytes
from time import sleep, time
from lxml import html
from urllib3 import disable_warnings
from threading import Thread, current_thread
from logging import getLogger, StreamHandler, Formatter, INFO

disable_warnings()

strings = ascii_letters + digits
domain = "example.com"
num_threads = 32

headers = {
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
}

proxies = {}

log = getLogger()
log.setLevel(INFO)
console_handler = StreamHandler()
console_handler.setLevel(INFO)
formatter = Formatter('[%(asctime)s %(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
log.addHandler(console_handler)

def randstr(chars, length):
    return ''.join(sample(chars, length))

def time_how(start):
    return f"{(time() - start):.2f}"

def get_code(email, num, time=10):
    time -= 1
    if time == 0:
        raise TimeoutError("get captcha code timeout")
    sleep(3)
    host = "pop.qq.com"
    port = 995
    username = "example@qq.com"
    password = "example"
    pop_server = POP3_SSL(host, port)
    pop_server.user(username)
    pop_server.pass_(password)
    count, _ = pop_server.stat()
    start = count
    end = max(1, count - (num - 1))
    for i in range(start, end - 1, -1):
        try:
            _, msg_lines, _ = pop_server.retr(i)
            msg_raw = b'\n'.join(msg_lines)
            email_message = message_from_bytes(msg_raw)
            to_header = email_message.get('To', '')
            if email not in to_header:
                continue
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    if content_type == 'text/html':
                        body = part.get_payload(decode=True).decode('utf-8')
                        break
            else:
                body = email_message.get_payload(decode=True).decode('utf-8')
            tree = html.fromstring(body)
            elements = tree.xpath('/html/body/div/div/div[2]/p[3]/strong/text()')
            if elements:
                code = elements[0].strip()
                pop_server.quit()
                return code
        except Exception as e:
            log.warning(f"({current_thread().name}) error processing email: {e}")
            continue
    pop_server.quit()
    return get_code(email, num, time)

def register(email):
    data = {
        "id": "",
        "email": email,
        "password": "",
        "name": "",
        "phone": "",
        "token": "",
        "credential": "",
        "from": "",
        "nobot": "true"
    }
    response = post('https://kunber.zone.id/api/login', headers=headers, json=data)
    json = response.json()
    if response.status_code != 201:
        return "login failed"
    login_token = json["token"]
    data = {
        "id": "",
        "email": email,
        "password": "@Abc12345678",
        "name": "Yuan Shen",
        "phone": "+123456789",
        "token": login_token,
        "credential": "",
        "from": "",
        "nobot": "true"
    }
    response = post("https://kunber.zone.id/api/register", headers=headers, json=data)
    json = response.json()
    if response.status_code != 200:
        return "pre-register failed"
    user_token_id = json["user_token_id"]
    response = post(f"https://kunber.zone.id/api/confirm/{user_token_id}/send-otp", headers=headers)
    if response.status_code != 200:
        return "send-otp failed"
    code = get_code(email, num_threads)
    data = {
        "token": code,
        "new_password": "",
        "step": 2
    }
    response = post(f"https://kunber.zone.id/api/confirm/{user_token_id}", headers=headers, json=data)
    if response.status_code != 200:
        return "verify failed"
    with open('accounts.txt', 'a') as f:
        f.write(f'{email}:@Abc12345678\n')
        f.close()
    return "successful"

def main():
    while True:
        try:
            start = time()
            email = f"{randstr(strings, 10)}@{domain}"
            result = register(email)
            log.info(f"({current_thread().name}) {email} {time_how(start)}s {result}")
        except Exception as e:
            log.warning(f"({current_thread().name}) {e}")

if __name__ == "__main__":
    threads = []

    for i in range(num_threads):
        thread = Thread(target=main, name=f"{i+1:03d}")
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
