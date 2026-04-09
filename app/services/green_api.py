import requests


def send_message(id_instance: str, api_token: str, chat_id: str, message: str):
    if not id_instance:
        raise Exception("id_instance is empty")

    if not api_token:
        raise Exception("api_token is empty")

    if not chat_id:
        raise Exception("chat_id is empty")

    if not message or not message.strip():
        raise Exception("message is empty")

    url = f"https://7107.api.greenapi.com/waInstance{id_instance}/sendMessage/{api_token}"

    payload = {
        "chatId": chat_id,
        "message": message.strip(),
    }

    print(f"GREEN API REQUEST: url={url}, chat_id={chat_id}, payload={payload}")

    response = requests.post(url, json=payload, timeout=30)

    print(f"GREEN API RESPONSE STATUS: {response.status_code}")
    print(f"GREEN API RESPONSE TEXT: {response.text[:1000]}")

    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text}

    if response.status_code >= 400:
        raise Exception(f"Green API error {response.status_code}: {data}")

    return data