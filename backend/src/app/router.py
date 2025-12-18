# src/app/router.py
import logging
import asyncio
from typing import Dict, Any, List

from fastapi import WebSocket

from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message
from src.message_structures.conversation import Conversation
from src.config.Role import Role

from src.agents.planner_agent import plan_with_model
from src.agents.read_write_agent import read_write  # your agent that returns summaries
from src.agents.agent_utils import TOOLS, TOOL_MAP

from src.tool_parsers.qwen3_4b_instruct_2507 import parse_qwen4b_tool_call
from src.tool_parsers.granite_4 import parse_granite_tool_call

logger = logging.getLogger("uvicorn.error")


async def handle_query(
        query: str,
        websocket: WebSocket,
        conversation_history: Conversation,
        model_manager: ModelManager):

    logger.info(f"Router handling query")

    # pick a model for planner/execution (use config mapping)
    planner_model = model_manager.config.models["QWEN3_4B_INSTRUCT_2507_Q6_K"]

    # Create a list of context objects to store
    context_store: Dict[str, str] = {}

    # Planner: ask for plan (planner can use tools)
    logger.info("🧭 Asking planner for an execution plan")
    plan = await plan_with_model(query, context_store, planner_model, model_manager)

    logger.info(f"🧭 Received plan with {len(plan)} steps")
    for i, s in enumerate(plan, start=1):
        logger.info(f"  {i}. {s.get('step')} — {s.get('tool', 'NO TOOL')} — {s.get('prompt')[:200]}")

    read_write_model = model_manager.config.models["QWEN3_4B_INSTRUCT_2507_Q6_K"] 

    # 2) Execute steps sequentially (MVP supports read_files/read_write style)
    step_results: List[Dict[str, Any]] = []
    for idx, step in enumerate(plan, start=1):
        step_name = step.get("step", "unknown")
        step_prompt = step.get("prompt", "")
        tool_call = step.get("tool")
        logger.info(f"▶️ Executing step {idx}/{len(plan)}: {step_name}")

        # Update step prompt to account for looping between tool calls
        step_prompt += f"""
        Here are the following results of what you executed previously {step_results}
        """

        if tool_call != "":
            # route to your read_write agent
            # read_write_model = model_manager.config.models["JAMBA-REASONING-3B-Q4_K_M"] 
            try:
                # read_write returns aggregated summaries (string)
                summary = await read_write(
                    step_prompt, 
                    model_manager, 
                    planner_model,
                    read_write_model)
                
                context_store[f"step_{idx}_{step_name}"] = summary
                step_results.append({"step": step_name, "ok": True, "result": summary})
                logger.info(f"📌 Step {idx} produced summary length {len(summary)}")
            except Exception as e:
                logger.exception(f"Step {idx} failed: {e}")
                step_results.append({"step": step_name, "ok": False, "error": str(e)})
        elif step_name in ("answer_query", "final_answer"):
            # if planner included a final step, we stop execution and go to final reasoning
            logger.info("Planner requested final answer step. Breaking to final reasoning.")
            break
        else:
            # Unknown step: ask the model directly for this step's prompt (don't allow it to use tools otherwise it gets confused)
            logger.info(f"Executing ad-hoc step '{step_name}', asking model directly for the step result (tools unavailable).")
            try:
                model_resp = await asyncio.to_thread(
                    model_manager.ask_model,
                    read_write_model,
                    [Message(role="user", content=step_prompt)],
                    # tools=TOOLS,
                    tool_choice="auto",
                )
                # best-effort content extraction similar to planner_agent._extract_content_from_response
                content = ""
                try:
                    if isinstance(model_resp, dict):
                        choice = model_resp.get("choices", [{}])[0]
                        msg = choice.get("message") or {}
                        if isinstance(msg, dict):
                            content = msg.get("content", "") or msg.get("text", "")
                        else:
                            content = str(msg)
                    else:
                        content = str(model_resp)
                except Exception:
                    content = str(model_resp)

                # If model produced tool calls, execute them (sequentially)
                tool_calls = parse_qwen4b_tool_call(content) or parse_granite_tool_call(content)
                if not tool_calls:
                    step_results.append({"step": step_name, "ok": True, "result": content})
                else:
                    # execute each tool call (sequential to keep order)
                    outputs = []
                    for tc in tool_calls:
                        exec_res = await _execute_tool_call_router(tc)
                        outputs.append(exec_res)
                        if exec_res.get("ok") and isinstance(exec_res.get("result"), str):
                            # append tool result to context store if it's a read
                            outputs[-1]["snippet"] = exec_res["result"][:2000]
                    step_results.append({"step": step_name, "ok": True, "tools": outputs})
            except Exception as e:
                logger.exception("Error handling unknown step.")
                step_results.append({"step": step_name, "ok": False, "error": str(e)})

    # 3) Build aggregated context from step_results / context_store
    aggregated_parts = []
    for r in step_results:
        aggregated_parts.append(f"STEP: {r.get('step')}\n")
        if r.get("ok") and "result" in r:
            aggregated_parts.append(r["result"])
        elif r.get("tools"):
            for t in r["tools"]:
                if t.get("ok") and isinstance(t.get("result"), str):
                    aggregated_parts.append(f"\n[Tool {t['name']} output (first 4000 chars)]:\n{t['result'][:4000]}\n")
                else:
                    aggregated_parts.append(f"\n[Tool {t.get('name')} error]: {t.get('error')}\n")
        else:
            aggregated_parts.append(str(r.get("error", "No result")))

    # also include context_store entries
    for k, v in context_store.items():
        aggregated_parts.append(f"\nCONTEXT {k}:\n{v}\n")

    aggregated_summary = "\n\n---\n\n".join(aggregated_parts)
    logger.info(f"📄 Aggregated summary length: {len(aggregated_summary)} characters")

    # 4) Final reasoning: stream final answer using aggregated_summary
    final_system = "You are a helpful assistant. Use the aggregated results below to answer the user's original question."
    final_user = f"""
    You have already run the following steps:\n\n{context_store.keys()}

    with the following results:\n\n{aggregated_summary}
    
    Use this information to answer the user's question:\n{query}
    """

    final_messages = [
        # Message(role="system", content=final_system),
        Message(role="user", content=final_user)
    ]

    logger.error(final_messages)

    logger.info("💬 Starting final reasoning stream...")
    async for chunk in model_manager.ask_model_stream(planner_model, final_messages):
        await websocket.send_json({"type": "final_response", "message": chunk["content"]})

    await websocket.send_json({"type": "final_response", "message": "[DONE]"})
    conversation_history.append_message(Message(role="assistant", content="[Streamed final response]"))

    logger.info("Finished handle_query")


# helper used inside this router for executing tool calls when needed
async def _execute_tool_call_router(tool_call: Dict[str, Any], timeout: float = 15.0) -> Dict[str, Any]:
    """
    Mirror of the earlier helper, but local to router. Executes a single tool_call dict and returns structured result.
    """
    try:
        fn_name = tool_call["function"]["name"]
        args_json = tool_call["function"].get("arguments", "{}")
        try:
            args = json.loads(args_json) if isinstance(args_json, str) else args_json
        except Exception:
            args = {}

        logger.info(f"🛠 Executing tool: {fn_name}({args})")

        if fn_name not in TOOL_MAP:
            msg = f"Unknown tool: {fn_name}"
            logger.error(msg)
            return {"ok": False, "name": fn_name, "error": msg}

        func = TOOL_MAP[fn_name]
        res = await asyncio.wait_for(asyncio.to_thread(func, **args), timeout=timeout)
        return {"ok": True, "name": fn_name, "result": res}
    except asyncio.TimeoutError:
        err = f"Tool {tool_call} timed out"
        logger.error(err)
        return {"ok": False, "name": tool_call.get("function", {}).get("name", "unknown"), "error": err}
    except Exception as e:
        logger.exception(f"Error executing tool call: {e}")
        return {"ok": False, "name": tool_call.get("function", {}).get("name", "unknown"), "error": str(e)}
