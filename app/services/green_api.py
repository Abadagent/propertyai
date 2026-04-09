import requests


def send_message(id_instance: str, api_token: str, chat_id: str, message: str):
    url = f"https://7107.api.greenapi.com/waInstance{id_instance}/sendMessage/{api_token}"

    payload = {
        "chatId": chat_id,
        "message": message,
    }

    response = requests.post(url, json=payload, timeout=30)

    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text}

    if response.status_code >= 400:
        raise Exception(f"Green API error {response.status_code}: {data}")

    return data