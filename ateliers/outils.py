import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from rag import CHAT_MODEL, OLLAMA, request_json


class Duree(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heures: int = Field(ge=0, le=72, strict=True)
    minutes: int = Field(ge=0, le=59, strict=True)


def duree_minutes(heures, minutes):
    duree = Duree(heures=heures, minutes=minutes)
    return 60 * duree.heures + duree.minutes


def main():
    tool_name = "duree_minutes"
    messages = [
        {"role": "system", "content": "استخدم الأداة المتاحة لتحويل المدة، ثم أجب بالعربية الفصحى."},
        {"role": "user", "content": "حوّل ساعتين و15 دقيقة إلى دقائق."},
    ]
    payload = {
        "model": CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"num_ctx": 4096, "num_predict": 192, "temperature": 0},
    }
    payload["tools"] = [{"type": "function", "function": {
        "name": tool_name,
        "description": "تحوّل الأداة مدة بالساعات والدقائق إلى إجمالي الدقائق.",
        "parameters": Duree.model_json_schema(),
    }}]
    message = request_json(f"{OLLAMA}/api/chat", "POST", payload)["message"]
    calls = message.get("tool_calls", [])
    if len(calls) != 1 or calls[0]["function"]["name"] != tool_name:
        raise SystemExit("لم يقترح النموذج استدعاء الأداة المتوقع. جرّب النموذج 8B.")
    try:
        arguments = Duree.model_validate(calls[0]["function"]["arguments"])
    except ValidationError as error:
        raise SystemExit("رُفض استدعاء الأداة لأن قيم المدة غير صالحة.") from error
    result = duree_minutes(arguments.heures, arguments.minutes)
    print(f"نتيجة الأداة بعد التحقق من المدخلات = {result} دقيقة")
    messages.extend([message, {
        "role": "tool", "tool_name": tool_name, "content": json.dumps({"minutes": result}),
    }])
    payload.pop("tools")
    final = request_json(f"{OLLAMA}/api/chat", "POST", payload)["message"]["content"]
    print(final)


if __name__ == "__main__":
    main()
