import httpx

SYSTEM_PROMPT = '''You are PenguCost AI, a cautious household fixed-cost analyst. Analyze only the provided structured expense data. Focus on concrete savings opportunities, upcoming expirations/cancellations, unusually high recurring costs, duplicate services, and realistic monthly savings. Never invent market prices or provider offers. Treat each expense's notes field as user-supplied context about why the service exists, its benefits, constraints, or intended use; use that context when judging whether a cost is realistically reducible. Never infer or use data from any user other than the data explicitly present in the payload. Clearly label assumptions. Reply in the user's requested language. Structure the response as: Summary, Quick wins, Upcoming attention, Savings plan.'''


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
