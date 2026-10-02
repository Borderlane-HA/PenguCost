from __future__ import annotations
import json
import httpx


class AIResponseError(RuntimeError):
    """Provider failure with a fixed, privacy-safe explanation (no response text)."""

    def __init__(self, reason: str):
        messages = {
            'missing_choices': 'AI provider returned no response choices. Check that the profile uses an OpenAI-compatible /v1 endpoint.',
            'empty': 'AI provider returned an empty final answer. Check the model and its chat template.',
            'thinking_only': 'AI provider returned reasoning but no final answer. Check the model thinking settings and available context window.',
            'truncated': 'AI response was cut off (token/context limit). For Ollama, use Automatic output and check its context window; otherwise increase the output limit or use fewer pages.',
            'filtered': 'AI provider stopped the response with content_filter. Check the provider or model policy.',
            'incomplete': 'Ollama returned an unfinished response. Check the model/server configuration.',
        }
        self.reason = reason
        super().__init__(messages[reason])

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


def _anthropic_content(content):
    if not isinstance(content, list):
        return content
    blocks = []
    for block in content:
        if block.get('type') == 'image_url':
            url = block['image_url']['url']
            if not url.startswith('data:image/') or ';base64,' not in url:
                raise RuntimeError('Only inline document images are supported')
            media_type, data = url[5:].split(';base64,', 1)
            blocks.append({'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': data}})
        else:
            blocks.append(block)
    return blocks


def _ollama_chat_url(base_url: str) -> str:
    base = base_url.rstrip('/')
    if not base:
        raise RuntimeError('Base URL is missing for this AI profile')
    for suffix in ('/v1/chat/completions', '/api/chat', '/chat/completions', '/v1'):
        if base.endswith(suffix):
            base = base[:-len(suffix)]
            break
    return base + '/api/chat'


def _ollama_messages(messages: list[dict]) -> list[dict]:
    """Keep all text and inline page images together in their original user turn."""
    result = []
    for message in messages:
        content = message['content']
        if isinstance(content, str):
            result.append(dict(message))
            continue
        text, images = [], []
        for block in content:
            if block.get('type') == 'text':
                text.append(block['text'])
            elif block.get('type') == 'image_url':
                url = block['image_url']['url']
                if not url.startswith('data:image/') or ';base64,' not in url:
                    raise RuntimeError('Only inline document images are supported')
                images.append(url.split(';base64,', 1)[1])
        converted = {'role': message['role'], 'content': '\n'.join(text)}
        if images:
            converted['images'] = images
        result.append(converted)
    return result


async def _call_model(provider: str, base_url: str, api_key: str, model: str, system: str, messages: list[dict], max_tokens: int = 3200, require_complete: bool = False, ollama_context_tokens: int | None = None) -> str:
    url, anthropic = _url(provider, base_url)
    timeout = httpx.Timeout(1800.0 if require_complete else 600.0, connect=30.0)
    if provider == 'ollama' and ollama_context_tokens is not None:
        options = {'temperature': 0.2, 'num_predict': max_tokens or -1}
        if ollama_context_tokens:
            options['num_ctx'] = ollama_context_tokens
        body = {'model': model, 'stream': False, 'format': 'json', 'think': False,
                'options': options,
                'messages': _ollama_messages([{'role': 'system', 'content': system}, *messages])}
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(_ollama_chat_url(base_url), json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
        if require_complete and data.get('done_reason') == 'length':
            error = AIResponseError('truncated')
            # Whitelisted numeric diagnostics only; never store model text/reasoning.
            counts = ', '.join(f'{key}={data[key]}' for key in ('prompt_eval_count', 'eval_count')
                               if type(data.get(key)) is int and 0 <= data[key] <= 2**31)
            detail = f'requested_context={ollama_context_tokens or "server default"}'
            error.args = (f'Ollama stopped with done_reason=length; {detail}'
                          + (f', {counts}' if counts else '')
                          + '. Increase the statement context setting or check the model/server limits.',)
            raise error
        if require_complete and data.get('done') is not True:
            raise AIResponseError('incomplete')
        message = data.get('message') or {}
        content = message.get('content')
        if not isinstance(content, str) or not content.strip():
            raise AIResponseError('thinking_only' if message.get('thinking') else 'empty')
        return content.strip()
    if anthropic:
        body = {
            'model': model,
            'max_tokens': max_tokens or 8000,
            'temperature': 0.2,
            'system': system,
            'messages': [{'role': m['role'], 'content': _anthropic_content(m['content'])} for m in messages if m['role'] in {'user', 'assistant'}],
        }
        headers = {'Content-Type': 'application/json', 'anthropic-version': '2023-06-01'}
        if api_key:
            headers['x-api-key'] = api_key
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
            if require_complete and data.get('stop_reason') == 'max_tokens':
                raise AIResponseError('truncated')
            content = data.get('content') or []
            if not content:
                raise AIResponseError('empty')
            result = ''.join(x.get('text', '') for x in content if isinstance(x, dict)).strip()
            if not result:
                raise AIResponseError('thinking_only' if any(x.get('type') == 'thinking' for x in content if isinstance(x, dict)) else 'empty')
            return result

    body = {
        'model': model,
        'temperature': 0.2,
        'messages': [{'role': 'system', 'content': system}, *messages],
    }
    if max_tokens:
        body['max_tokens'] = max_tokens
    elif provider == 'ollama':
        # Ollama 0.34.4 maps max_tokens directly to num_predict. -1 explicitly
        # removes the prediction cap, including a cap stored in a Modelfile.
        body['max_tokens'] = -1
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
        choices = data.get('choices') or []
        if not choices:
            raise AIResponseError('missing_choices')
        finish = choices[0].get('finish_reason')
        if require_complete and finish == 'length':
            raise AIResponseError('truncated')
        if require_complete and finish == 'content_filter':
            raise AIResponseError('filtered')
        message = choices[0].get('message') or {}
        content = message.get('content')
        if not isinstance(content, str) or not content.strip():
            reasoning = message.get('reasoning') or message.get('reasoning_content') or message.get('thinking')
            raise AIResponseError('thinking_only' if reasoning else 'empty')
        return content.strip()


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
