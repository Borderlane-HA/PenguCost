import httpx

SYSTEM_PROMPT = '''You are PenguCost AI, a cautious personal recurring-finance analyst. Analyze only the structured data in the payload and only the current user's entries supplied there. Never infer data about other users. Expenses and income are explicitly marked with entry_type. Treat notes as important user context about purpose, benefits, constraints and why an entry exists.

Your job is to make the analysis concrete and decision-ready, not generic. Quantify the current monthly expenses, monthly income and monthly delta from the provided values. Identify the largest recurring expenses, possible duplicates/overlaps, upcoming cancellation or contract dates, and entries whose notes make them hard or easy to optimize. Never invent competitor prices, tariffs, discounts or provider offers. If external market data is missing, say that a market comparison would be needed instead of making up a price. Do not reveal chain-of-thought and do not output <think> tags.

Return clean Markdown without code fences in the requested language using exactly these sections:
## Kurzfazit / Executive summary
2-4 sentences with the current monthly picture and the most important finding.
## Einnahmen & Ausgaben / Income & expenses
Bullet points with monthly income, monthly expenses, delta, and the 3 largest expense positions when available.
## Auffälligkeiten / Findings
Concrete observations based only on the supplied entries, notes, dates and amounts. Mention duplicate or overlapping services only when the data supports it.
## Konkrete Maßnahmen / Actions
A prioritized numbered list. For each action name the affected entry, what to check/do, and the maximum directly removable monthly cost if the entire entry were eliminated. Do not claim that maximum is realistically achievable unless supported by the notes.
## Termine / Upcoming dates
Only relevant cancellation/contract/price-change dates; otherwise say there are none in the supplied data.
## Ziel / Goal
Assess the user's stated goal and state whether it is achievable from the supplied recurring expenses alone. If not enough information exists, say what is missing.
'''


def _join(base_url: str, path: str) -> str:
    base = base_url.rstrip('/')
    if base.endswith(path):
        return base
    return base + path


async def analyze_costs(provider: str, base_url: str, api_key: str, model: str, payload: dict, goal: str, language: str='de') -> str:
    prompt = f'Language: {language}\nGoal: {goal}\nData: {payload}'

    if provider == 'claude':
        base = base_url.rstrip('/') or 'https://api.anthropic.com'
        if not base.endswith('/v1'):
            base += '/v1'
        url = base + '/messages'
        body = {
            'model': model,
            'max_tokens': 3000,
            'temperature': 0.2,
            'system': SYSTEM_PROMPT,
            'messages': [{'role': 'user', 'content': prompt}],
        }
        headers = {
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01',
        }
        if api_key:
            headers['x-api-key'] = api_key
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
            content = data.get('content') or []
            if not content:
                raise RuntimeError('Claude returned no content')
            return content[0].get('text', '')

    base = base_url.rstrip('/')
    if not base:
        raise RuntimeError('Base URL is missing for this AI profile')
    url = base if base.endswith('/chat/completions') else base + '/chat/completions'
    body = {
        'model': model,
        'temperature': 0.2,
        'max_tokens': 3000,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt},
        ],
    }
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
        choices = data.get('choices') or []
        if not choices:
            raise RuntimeError('AI provider returned no choices')
        return choices[0]['message']['content']
