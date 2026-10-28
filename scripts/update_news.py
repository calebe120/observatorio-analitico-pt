import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# Fuso horário de Brasília (UTC-3)
BRT = timezone(timedelta(hours=-3))
hoje_str = datetime.now(BRT).strftime("%d/%m/%Y")

meses = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}
dias_semana = {
    0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira",
    3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"
}
agora = datetime.now(BRT)
data_extenso = f"{dias_semana[agora.weekday()]}, {agora.day} de {meses[agora.month]} de {agora.year}"

# 1. Coleta de Feeds Oficiais (Agência Brasil, Senado e Câmara)
FEEDS = [
    ("Agência Brasil - Política", "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml"),
    ("Agência Brasil - Economia", "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml"),
    ("Agência Senado", "https://www12.senado.leg.br/noticias/feed/todasnoticias"),
]

noticias_coletadas = []

for nome_fonte, url in FEEDS:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item')[:8]:
                titulo = item.findtext('title') or ''
                link = item.findtext('link') or ''
                desc = item.findtext('description') or ''
                noticias_coletadas.append(f"[{nome_fonte}] Título: {titulo} | Resumo: {desc[:250]} | Link: {link}")
    except Exception as e:
        print(f"Aviso ao ler {nome_fonte}: {e}")

bloco_noticias = "\n".join(noticias_coletadas[:22])

# 2. Chamada à API do Gemini para Análise Imparcial e Checagem
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("A variável GEMINI_API_KEY não foi configurada nos Secrets do GitHub.")

prompt = f"""
Você é o editor-chefe apartidário do portal 'Observatório Analítico — Monitor PT & Governo Federal'.
Data de hoje: {data_extenso} ({hoje_str}).

Abaixo estão as notícias oficiais coletadas hoje da Agência Brasil e Agência Senado:
{bloco_noticias}

Gere um JSON estrito (sem formatação markdown) contendo:
1. "updatedDate": "{hoje_str}"
2. "fullDateText": "{data_extenso}"
3. "items": lista com 6 análises principais do dia. Cada item deve ter:
   - "id": identificador único (slug)
   - "category": escolha apenas entre "fiscal", "checagem", "congresso" ou "partido"
   - "categoryLabel": nome legível da categoria
   - "badgeColor": "rose" (para fiscal), "emerald" (para checagem), "indigo" (para congresso/partido) ou "amber" (para economia/tributos)
   - "date": "{hoje_str}"
   - "verdict": selo curto em maiúsculas (ex: "EM VOTAÇÃO NO CONGRESSO", "MEDIDA OFICIAL", "CORTE ORÇAMENTÁRIO")
   - "title": título jornalístico imparcial e direto
   - "summary": resumo factual contextualizado
   - "positiveSideTitle": título do argumento governamental/avanço
   - "positiveSide": explicação técnica do ponto positivo ou posição oficial do governo
   - "criticalSideTitle": título do impacto fiscal, cobrança, risco ou ponto crítico da oposição/mercado
   - "criticalSide": explicação técnica do ponto crítico, custo ou limitação prática
   - "sources": lista de objetos [{{"label": "Nome da Fonte Oficial", "url": "URL real retirada da lista acima"}}]
4. "factChecks": lista com 5 itens de checagem (Fato vs. Boato). Cada item deve ter:
   - "question": pergunta direta que o cidadão pesquisa
   - "status": selo curto ("CONFIRMADO", "BOATO / FALSO", "LEI SANCIONADA", "AINDA NÃO VALE")
   - "statusColor": "emerald", "rose" ou "amber"
   - "explanation": explicação clara e direta com fatos
   - "sourceLabel": nome da fonte
   - "sourceUrl": URL real da lista acima
"""

payload = json.dumps({
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "temperature": 0.2,
        "responseMimeType": "application/json"
    }
}).encode("utf-8")

gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
req = urllib.request.Request(gemini_url, data=payload, headers={"Content-Type": "application/json"})

with urllib.request.urlopen(req, timeout=60) as resp:
    result = json.loads(resp.read().decode("utf-8"))
    texto_json = result["candidates"][0]["content"]["parts"][0]["text"]
    dados_finais = json.loads(texto_json)

with open("news_data.json", "w", encoding="utf-8") as f:
    json.dump(dados_finais, f, ensure_ascii=False, indent=2)

print("news_data.json atualizado com sucesso!")
