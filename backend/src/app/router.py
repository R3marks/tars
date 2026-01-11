# src/app/router.py
import json
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
    plan = await plan_with_model(
        query, 
        context_store, 
        planner_model, 
        model_manager)

    steps = plan["steps"]
    logger.info(f"🧭 Received plan with {len(steps)} steps")

    for i, s in enumerate(steps, start=1):
        logger.info(f"  {i}. {s.get('step')} — {s.get('tool', 'NO TOOL')} — {s.get('prompt')[:200]}")

    read_write_model = model_manager.config.models["QWEN3_4B_INSTRUCT_2507_Q6_K"] 

    # 2) Execute steps sequentially (MVP supports read_files/read_write style)
    step_results: List[Dict[str, Any]] = []

    for idx, step in enumerate(steps, start=1):
        step_name = step["step"]
        step_prompt = step["prompt"]
        tool_call = step["tool"]

        logger.info(f"▶️ Executing step {idx}/{len(steps)}: {step_name}")

        # Update step prompt to account for looping between tool calls
        step_prompt += f"""
        Here are the following results of what you executed previously {step_results}
        """
        logger.error(step)
        if tool_call:
            try:
                # read_write returns aggregated summaries (string)
                summary = await read_write(
                    step_prompt, 
                    model_manager, 
                    planner_model,
                    read_write_model)
                
                context_store[f"step_{idx}_{step_name}"] = summary
                step_results.append({
                    "step": step_name, 
                    "ok": True, 
                    "tool": tool_call, 
                    "result": summary
                    })
                logger.info(f"📌 Step {idx} produced summary length {len(summary)}")
            except Exception as e:
                logger.exception(f"Step {idx} failed: {e}")
                step_results.append({
                    "step": step_name, 
                    "ok": False,
                    "tool": tool_call,
                    "result": str(e)
                    })
        else:
            logger.info(f"Executing step '{step_name}' without tools")
            step_prompt_message = [Message(
                role="user", 
                content=step_prompt
                )
            
            ]
            try:
                step_response = await asyncio.to_thread(
                    model_manager.ask_model,
                    read_write_model,
                    step_prompt_message,
                    # tools=TOOLS,
                    tool_choice="auto",
                )

                step_results.append({
                    "step": step_name, 
                    "ok": True,
                    "tool": "None",
                    "result": step_response})
            except Exception as e:
                logger.exception("Error handling unknown step.")
                step_results.append({
                    "step": step_name, 
                    "ok": False,
                    "tool": "None",
                    "result": str(e)})

    # 3) Build aggregated context from step_results / context_store
    aggregated_parts = []
    for step_result in step_results:
        aggregated_parts.append(f"STEP: {step_result.get('step')}\n")
        aggregated_parts.append(step_result["result"])

    # also include context_store entries
    for k, v in context_store.items():
        aggregated_parts.append(f"\nCONTEXT {k}:\n{v}\n")

    aggregated_summary = "\n\n---\n\n".join(aggregated_parts)
    logger.info(f"📄 Aggregated summary length: {len(aggregated_summary)} characters")

    # 4) Final reasoning: stream final answer using aggregated_summary
    #     with the following results:\n\n{aggregated_summary}
    final_user = f"""
    You have already run the following steps:\n\n{context_store.items()}
    
    Use this information to answer the user's question:\n{query}
    """

    final_messages = [
        Message(role="user", content=final_user)
    ]

    logger.info("💬 Starting final reasoning stream...")
    summary_model = model_manager.config.models["QWEN3_4B_INSTRUCT_2507_Q6_K"]

    async for chunk in model_manager.ask_model_stream(summary_model, final_messages):
        await websocket.send_json({
            "type": "final_response", 
            "message": chunk["content"]
            })

    await websocket.send_json({
        "type": "final_response", 
        "message": "[DONE]"
        })
    
    conversation_history.append_message(Message(role="assistant", content="[Streamed final response]"))

    logger.info("Finished handle_query")