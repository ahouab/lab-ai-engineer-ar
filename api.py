from fastapi import FastAPI
from fastapi.responses import JSONResponse

from rag import ALIAS, CHAT_MODEL, EMBED_MODEL, OLLAMA, QDRANT, Question, ServiceError
from rag import answer, request_json, retrieve


app = FastAPI(
    title="مساعد أدلة التشغيل لمختبر مهندس الذكاء الاصطناعي",
    description="واجهة محلية للبحث في أدلة التشغيل والإجابة عنها مع ذكر المصادر.",
    redoc_url=None,
)


@app.exception_handler(ServiceError)
async def dependency_error(_request, error):
    return JSONResponse(status_code=503, content={"detail": str(error)})


@app.get("/healthz", summary="فحص تشغيل الواجهة")
def health():
    return {"status": "up"}


@app.get("/readyz", summary="فحص جاهزية النماذج وفهرس المستندات")
def ready():
    models = request_json(f"{OLLAMA}/api/tags", timeout=5)
    names = {model["name"] for model in models["models"]}
    required = {name if ":" in name else f"{name}:latest" for name in (CHAT_MODEL, EMBED_MODEL)}
    missing = required - names
    if missing:
        return JSONResponse(status_code=503, content={"missing_models": sorted(missing)})
    request_json(f"{QDRANT}/collections/{ALIAS}", timeout=5)
    return {"status": "ready", "chat_model": CHAT_MODEL, "embedding_model": EMBED_MODEL}


@app.post("/search", summary="البحث عن المقاطع ذات الصلة")
def search(body: Question):
    return {"sources": retrieve(body.question)}


@app.post("/ask", summary="الإجابة عن سؤال مع ذكر المصادر")
def ask(body: Question):
    return answer(body.question)
