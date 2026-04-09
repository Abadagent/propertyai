import time
import requests

LAST_SEND_TIME = {}


def rate_limit(instance_id: str, delay: float = 1.5):
    last_time = LAST_SEND_TIME.get(instance_id, 0)
    now = time.time()

    diff = now - last_time
    if diff < delay:
        time.sleep(delay - diff)

    LAST_SEND_TIME[instance_id] = time.time()


def _build_error_message(response: requests.Response) -> str:
    try:
        body = response.json()
    except Exception:
        body = response.text

    return f"Green API error: status={response.status_code}, body={body}"


def send_message(id_instance: str, api_token: str, chat_id: str, text: str):
    rate_limit(id_instance)

    api_url = f"https://api.greenapi.com/waInstance{id_instance}/sendMessage/{api_token}"

    payload = {
        "chatId": chat_id,
        "message": text
    }

    try:
        response = requests.post(api_url, json=payload, timeout=30)

        if response.status_code == 429:
            time.sleep(2)
            response = requests.post(api_url, json=payload, timeout=30)

        if not response.ok:
            raise Exception(_build_error_message(response))

        return response

    except requests.RequestException as e:
        raise Exception(f"Request to Green API failed: {str(e)}")