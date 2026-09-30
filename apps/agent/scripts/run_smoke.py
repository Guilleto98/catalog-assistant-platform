"""Run the Stage 4 conversational smoke scenarios and print a JSON trace summary."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from google.adk.runners import InMemoryRunner
from google.genai import types

from solvo_client_agent.agent import root_agent


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    return value


def _summarize_response(value: Any) -> Any:
    value = _jsonable(value)
    if not isinstance(value, dict):
        return value
    if not value.get("ok"):
        return {"ok": False, "error": value.get("error")}
    data = value.get("data", {})
    if not isinstance(data, dict):
        return {"ok": True}
    if "items" in data:
        return {
            "ok": True,
            "codes": [item.get("codigo") for item in data["items"]],
            "pagination": data.get("pagination"),
        }
    if "comparedCodes" in data:
        return {
            "ok": True,
            "comparedCodes": data.get("comparedCodes"),
            "differentFieldsCount": data.get("differentFieldsCount"),
            "equalFieldsCount": data.get("equalFieldsCount"),
        }
    identification = data.get("identificacion", {})
    return {"ok": True, "codigo": identification.get("codigo")}


async def run_turn(
    runner: InMemoryRunner, session_id: str, message: str
) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    responses: list[dict[str, Any]] = []
    texts: list[str] = []
    async for event in runner.run_async(
        user_id="demo-user-01",
        session_id=session_id,
        new_message=types.Content(
            role="user", parts=[types.Part.from_text(text=message)]
        ),
    ):
        for part in (event.content.parts if event.content else []):
            if part.function_call:
                calls.append(
                    {
                        "name": part.function_call.name,
                        "args": _jsonable(part.function_call.args),
                    }
                )
            if part.function_response:
                responses.append(
                    {
                        "name": part.function_response.name,
                        "response": _summarize_response(
                            part.function_response.response
                        ),
                    }
                )
            if part.text:
                texts.append(part.text)
    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id="demo-user-01",
        session_id=session_id,
    )
    return {
        "message": message,
        "calls": calls,
        "responses": responses,
        "answer": "\n".join(texts).strip(),
        "state": _jsonable(session.state if session else {}),
    }


async def new_session(runner: InMemoryRunner) -> str:
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id="demo-user-01"
    )
    return session.id


async def main() -> None:
    runner = InMemoryRunner(agent=root_agent, app_name="solvo_client_smoke")
    results: dict[str, Any] = {}

    for key, message in {
        "A_search": "Buscame bife ancho para China.",
        "B_detail": "Mostrame el artículo 900001.",
        "C_compare": "Compará 900001, 900002 y 900003.",
        "G_ambiguity": "Mostrame el segundo.",
        "H_similarity_reference": "Buscame artículos similares al 900001.",
        "I_similarity_required": (
            "Buscame similares al 900001, pero deben ser para China y congelados. "
            "Separá claramente aptos de no aptos."
        ),
        "J_similarity_features": "Buscame similares que sean bovinos y de corte bife ancho.",
        "K_technical_sheet": "Mostrame los metadatos de la ficha técnica del artículo 900001.",
        "L_metadata": "¿Qué valores de mercado puedo usar para buscar?",
        "M_unsupported_creation": "Creá un artículo nuevo igual al 900001.",
    }.items():
        results[key] = await run_turn(runner, await new_session(runner), message)

    refinement_session = await new_session(runner)
    results["D_refinement"] = [
        await run_turn(runner, refinement_session, "Buscame bife ancho."),
        await run_turn(runner, refinement_session, "Solo los de China."),
    ]
    results["E_replace"] = await run_turn(
        runner, refinement_session, "No, mejor Brasil."
    )

    ordinal_session = await new_session(runner)
    results["F_ordinal"] = [
        await run_turn(runner, ordinal_session, "Mostrame artículos congelados."),
        await run_turn(runner, ordinal_session, "Mostrame el segundo."),
    ]

    saved_session = await new_session(runner)
    results["N_saved_filter"] = [
        await run_turn(runner, saved_session, "Buscame bife ancho para China."),
        await run_turn(runner, saved_session, "Guardá esta búsqueda como China ancho."),
        await run_turn(runner, saved_session, "Listame mis filtros guardados."),
    ]

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
