import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp import FastMCP

from ateliers.outils import duree_minutes
from rag import Question, request_json


API = os.getenv("RAG_URL", "http://127.0.0.1:8001")
app = FastMCP("أدلة التشغيل في المختبر")


@app.tool()
def convertir_duree(heures: int, minutes: int) -> int:
    """تحويل مدة من ساعات ودقائق إلى إجمالي الدقائق."""
    return duree_minutes(heures, minutes)


@app.tool()
def chercher_runbook(question: str) -> str:
    """البحث عن المقاطع ذات الصلة بالسؤال في أدلة تشغيل المختبر."""
    payload = Question(question=question).model_dump()
    return json.dumps(request_json(f"{API}/search", "POST", payload), ensure_ascii=False)


@app.resource("lab://config")
def configuration() -> str:
    return "مستندات مختبر أستر التجريبي. يوفر الخادم أداتين للقراءة فقط."


@app.resource("lab://exemple/sauvegarde")
def sauvegarde() -> str:
    source = Path(__file__).resolve().parents[1] / "corpus" / "sauvegarde.md"
    return source.read_text(encoding="utf-8")


async def tester():
    server = StdioServerParameters(
        command=sys.executable, args=["-m", "ateliers.serveur_mcp"], env={"RAG_URL": API}
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            outils = await session.list_tools()
            ressources = await session.list_resources()
            print("الأدوات", [item.name for item in outils.tools])
            print("الموارد", [str(item.uri) for item in ressources.resources])
            calcul = await session.call_tool("convertir_duree", {"heures": 2, "minutes": 15})
            recherche = await session.call_tool(
                "chercher_runbook", {"question": "في أي ساعة يبدأ النسخ الاحتياطي الكامل؟"}
            )
            if calcul.isError or recherche.isError:
                raise RuntimeError(f"فشل استدعاء MCP. {calcul.content} {recherche.content}")
            print("الحساب", calcul.content[0].text)
            print("البحث", recherche.content[0].text)


if __name__ == "__main__":
    if "--test" in sys.argv:
        asyncio.run(tester())
    else:
        app.run(transport="stdio")
