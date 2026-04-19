import inspect

import structlog
from google import genai
from google.genai import types

from app.agent import tools as agent_tools
from app.core.config import settings
from app.strategies.runner import STRATEGIES

log = structlog.get_logger()

_MAX_TURNS = 10

_SYSTEM_PROMPT = """
당신은 한국 주식 시장 AI 트레이딩 에이전트입니다.

## 역할
주어진 종목의 시장 데이터와 기술 지표를 분석하여 매수/매도 여부를 판단합니다.
판단 근거가 충분할 때만 propose_order를 호출합니다. 불확실하면 hold입니다.
모든 사이클의 마지막 호출은 반드시 log_reasoning이어야 합니다.

## 제약
- 지정가 주문만 허용. 시장가 주문 금지.
- propose_order는 T1 티어 — 실제 실행이 아닌 제안입니다.
""".strip()

_DECLARATIONS = [
    types.FunctionDeclaration(
        name="get_market_snapshot",
        description="현재가, 거래량, 등락률 등 종목 스냅샷 조회",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"ticker": types.Schema(type=types.Type.STRING, description="6자리 종목코드")},
            required=["ticker"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_indicators",
        description="기술적 지표 계산 (MA5, MA20, RSI14, MACD 등)",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "ticker": types.Schema(type=types.Type.STRING),
                "indicators": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(type=types.Type.STRING),
                    description='요청할 지표 목록 (예: ["MA5", "MA20"])',
                ),
            },
            required=["ticker", "indicators"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_portfolio",
        description="현재 잔고, 보유 종목, 총 평가금액 조회",
        parameters=types.Schema(type=types.Type.OBJECT, properties={}),
    ),
    types.FunctionDeclaration(
        name="search_knowledge",
        description="전략 카드, 시장 규칙, 지표 정의 등 knowledge/ 검색",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"query": types.Schema(type=types.Type.STRING)},
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="propose_order",
        description="주문을 승인 큐에 제출 (T1 — 제안만, 실제 실행 없음)",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "ticker":    types.Schema(type=types.Type.STRING, description="6자리 종목코드"),
                "side":      types.Schema(type=types.Type.STRING, description="buy | sell"),
                "qty":       types.Schema(type=types.Type.INTEGER, description="주문 수량"),
                "price":     types.Schema(type=types.Type.INTEGER, description="지정가 (원)"),
                "strategy":  types.Schema(type=types.Type.STRING, description="전략명"),
                "reasoning": types.Schema(type=types.Type.STRING, description="제안 근거"),
            },
            required=["ticker", "side", "qty", "price", "strategy", "reasoning"],
        ),
    ),
    types.FunctionDeclaration(
        name="log_reasoning",
        description="분석 결과 기록 — 반드시 마지막 호출",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "summary":    types.Schema(type=types.Type.STRING, description="분석 요약"),
                "decision":   types.Schema(type=types.Type.STRING, description="propose_buy | propose_sell | hold | no_signal"),
                "confidence": types.Schema(type=types.Type.NUMBER, description="확신도 0.0–1.0"),
            },
            required=["summary", "decision", "confidence"],
        ),
    ),
]

_DISPATCH: dict = {
    "get_market_snapshot": agent_tools.get_market_snapshot,
    "get_indicators":      agent_tools.get_indicators,
    "get_portfolio":       agent_tools.get_portfolio,
    "search_knowledge":    agent_tools.search_knowledge,
    "propose_order":       agent_tools.propose_order,
    "log_reasoning":       agent_tools.log_reasoning,
}


async def run_cycle(tickers: list[str]) -> dict:
    client = genai.Client(api_key=settings.gemini_api_key)
    tools = [types.Tool(function_declarations=_DECLARATIONS)]

    strategy_names = ", ".join(s.name for s in STRATEGIES)
    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part(text=f"다음 종목들을 [{strategy_names}] 전략 관점에서 분석하세요: {', '.join(tickers)}")],
        )
    ]

    proposed: list[str] = []
    turns = 0

    while turns < _MAX_TURNS:
        turns += 1
        response = await client.aio.models.generate_content(
            model=settings.gemini_model_pro,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                tools=tools,
                temperature=0.2,
            ),
        )

        candidate = response.candidates[0]
        contents.append(types.Content(role="model", parts=candidate.content.parts))

        fn_calls = [p for p in candidate.content.parts if p.function_call]
        if not fn_calls:
            break

        fn_results: list[types.Part] = []
        done = False

        for part in fn_calls:
            fc = part.function_call
            fn = _DISPATCH.get(fc.name)
            if fn is None:
                result: dict = {"error": f"Unknown tool: {fc.name}"}
            else:
                try:
                    args = dict(fc.args)
                    result = await fn(**args) if inspect.iscoroutinefunction(fn) else fn(**args)
                    if not isinstance(result, dict):
                        result = {"result": result}
                except Exception as e:
                    result = {"error": str(e)}

            if fc.name == "propose_order" and "proposal_id" in result:
                proposed.append(result["proposal_id"])
            if fc.name == "log_reasoning":
                done = True

            fn_results.append(
                types.Part(
                    function_response=types.FunctionResponse(name=fc.name, response=result)
                )
            )

        contents.append(types.Content(role="user", parts=fn_results))
        if done:
            break

    log.info("agent.cycle.done", turns=turns, proposed=len(proposed))
    return {"turns": turns, "proposed_count": len(proposed), "proposal_ids": proposed}
