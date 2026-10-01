from __future__ import annotations
import json
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

AGENT_PROMPT = '''You are PenguCost AI Agent, a persistent finance copilot for recurring income, expenses, subscriptions and contracts. Your purpose is to help the current user understand their finances and take specific, safe next steps.

Hard rules:
- Use only FINANCE_DATA_JSON, BRAIN_MEMORY and the current conversation. Never infer or mention other users.
- Start from the numbers: monthly income, expenses, delta, largest positions, relevant dates and known future price/renewal changes.
- Notes are first-class context. Essential=true means protected unless the user explicitly asks to challenge it.
- Never invent competitor prices, tariffs, discounts, market facts or cancellation rules. Say when external comparison data is needed.
- Distinguish current facts from forecast assumptions. For future years explain which contracts/prices cause the projection.
- Detect only evidence-backed duplicates/overlaps.
- Never reveal chain-of-thought or <think> tags.
- Use concise, clean Markdown in the requested language.

Behaviors:
ANALYSIS: Give a decision-ready cost check. Start with a one-line financial snapshot. Then identify 3-7 concrete findings ordered by impact. For every finding name the entry, exact monthly value, why it matters, and a practical next action. Mention upcoming cancellation/contract/renewal/price dates. End with 2-4 suggested follow-up questions the user can ask.
SAVINGS: Work backwards from the monthly savings target. Build a prioritized plan with exact candidate amounts, realistic contribution, cumulative savings and remaining gap. Protect essential items by default. If the target cannot be met from selected recurring expenses, say so clearly.
CHAT: Answer naturally and quantitatively. Support questions such as: compare years, explain forecast changes, identify expiring contracts, find price increases, detect overlaps, test 'what-if I remove X', or rank optimization candidates.

When useful, format findings in a compact Markdown table with columns Position | Monthly | Finding | Action. For comparisons, explicitly show before/after or year/year deltas. Do not repeat generic finance advice that is not tied to the supplied entries.'''


def _url(provider: str, base_url: str) -> tuple[str, bool]:
    if provider == 'claude':
        base = base_url.rstrip('/') or 'https://api.anthropic.com'
        if not base.endswith('/v1'):
            base += '/v1'
        return base + '/messages', True
    base = base_url.rstrip('/')
    if not base:
        raise RuntimeError('Base URL is missing for this AI profile')
    return (base if base.endswith('/chat/completions') else base + '/chat/completions'), False


async def _call_model(provider: str, base_url: str, api_key: str, model: str, system: str, messages: list[dict], max_tokens: int = 3200) -> str:
    url, anthropic = _url(provider, base_url)
    timeout = httpx.Timeout(600.0, connect=30.0)
    if anthropic:
        body = {
            'model': model,
            'max_tokens': max_tokens,
            'temperature': 0.2,
            'system': system,
            'messages': [{'role': m['role'], 'content': m['content']} for m in messages if m['role'] in {'user', 'assistant'}],
        }
        headers = {'Content-Type': 'application/json', 'anthropic-version': '2023-06-01'}
        if api_key:
            headers['x-api-key'] = api_key
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
            content = data.get('content') or []
            if not content:
                raise RuntimeError('Claude returned no content')
            return ''.join(x.get('text', '') for x in content if isinstance(x, dict)).strip()

    body = {
        'model': model,
        'temperature': 0.2,
        'max_tokens': max_tokens,
        'messages': [{'role': 'system', 'content': system}, *messages],
    }
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
        choices = data.get('choices') or []
        if not choices:
            raise RuntimeError('AI provider returned no choices')
        return (choices[0].get('message') or {}).get('content', '').strip()


async def analyze_costs(provider: str, base_url: str, api_key: str, model: str, payload: dict, goal: str, language: str='de') -> str:
    prompt = f'Language: {language}\nGoal: {goal}\nData: {payload}'
    return await _call_model(provider, base_url, api_key, model, SYSTEM_PROMPT, [{'role': 'user', 'content': prompt}], 3000)


def _missing_finance_data_reply(text: str) -> bool:
    """Detect a common model failure where supplied finance JSON is ignored.

    Some local OpenAI-compatible chat templates strongly prioritize the final user
    message and can overlook context sent in an earlier turn. We only trigger a
    retry when the model explicitly claims that the named finance payload is
    missing/not supplied.
    """
    value = ' '.join((text or '').lower().split())
    if 'finance_data_json' not in value:
        return False
    markers = (
        'nicht bereitgestellt', 'nicht zur verfügung', 'keine finanzdaten',
        'keine spezifischen finanzdaten', 'nicht erhalten', 'nicht vorhanden',
        'not provided', 'no finance data', 'no financial data', 'missing',
        'not supplied', 'not available',
    )
    return any(marker in value for marker in markers)


async def chat_finances(provider: str, base_url: str, api_key: str, model: str, finance_data: dict, brain: str, history: list[dict], user_message: str, language: str, mode: str='chat', target_savings: float | None=None) -> str:
    """Run one PenguCost agent turn.

    The authoritative finance payload is deliberately embedded in the *latest*
    user turn together with the user's request. This is more compatible with
    local/Ollama chat templates (including Gemma-family templates) that may give
    much less attention to an older context-only user turn.
    """
    target = '' if target_savings is None else f'\nMONTHLY_SAVINGS_TARGET_EUR: {target_savings:.2f}'
    entries = finance_data.get('entries') or []
    context = (
        f'LANGUAGE: {language}\nMODE: {mode.upper()}{target}\n'
        f'FINANCE_ENTRY_COUNT: {len(entries)}\n'
        f'BRAIN_MEMORY:\n{brain or "(empty)"}\n\n'
        'AUTHORITATIVE CURRENT-USER FINANCE DATA follows. It is present in this same user message. '
        'If FINANCE_ENTRY_COUNT is greater than 0, do not claim that finance data was not supplied.\n'
        f'FINANCE_DATA_JSON:\n{json.dumps(finance_data, ensure_ascii=False, default=str, indent=2)}\n\n'
        f'USER_REQUEST:\n{user_message}'
    )
    messages = [m for m in history[-14:] if m.get('role') in {'user', 'assistant'}]
    messages.append({'role': 'user', 'content': context})
    reply = await _call_model(provider, base_url, api_key, model, AGENT_PROMPT, messages, 3600)

    # Defensive compatibility retry for models that still ignore multi-turn context.
    # The second attempt is intentionally single-turn and therefore cannot lose the
    # finance payload behind prior chat history.
    if entries and _missing_finance_data_reply(reply):
        retry_context = (
            context
            + '\n\nIMPORTANT RETRY: The JSON above contains '
            + str(len(entries))
            + ' selected finance entries. Analyze those entries now. Do not ask the user to provide the finance data again.'
        )
        reply = await _call_model(
            provider, base_url, api_key, model, AGENT_PROMPT,
            [{'role': 'user', 'content': retry_context}], 3600,
        )
    return reply
