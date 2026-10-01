import httpx

SYSTEM_PROMPT = '''You are PenguCost AI, a cautious household fixed-cost analyst. Analyze only the provided structured expense data. Focus on concrete savings opportunities, upcoming expirations/cancellations, unusually high recurring costs, duplicate services, and realistic monthly savings. Never invent market prices or provider offers. Clearly label assumptions. Reply in the user's requested language. Structure the response as: Summary, Quick wins, Upcoming attention, Savings plan.'''

async def analyze_costs(base_url: str, api_key: str, model: str, payload: dict, goal: str, language: str='de') -> str:
    url = base_url.rstrip('/') + '/chat/completions'
    body = {
        'model': model,
        'temperature': 0.2,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': f'Language: {language}\nGoal: {goal}\nData: {payload}'},
        ],
    }
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
