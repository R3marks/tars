# src/agents/executor_agent.py
import json
import logging
from typing import Dict, Any, List

from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message
from src.agents.agent_utils import TOOL_MAP, TOOLS

logger = logging.getLogger("uvicorn.error")


async def execute_step(
        step_index: int,
        step: Dict[str, Any],
        steps: List[Dict[str, Any]],
        context: List[Dict[str, Any]],
        execution_results,
        model: Model,
        model_manager: ModelManager
    ) -> str:
        
        step_names = [step["step"] for step in steps]

        logger.info(f"🗣️  Prompt provided to the executor agent: {step["prompt"]}")

        prompt = f"""
        Given your position within a tree of agents, visualised like so:
        ---
        Layer 1: Expected Outcomes Agent generates `expected_outcomes`
        for `expected_outcome` in expected_outcomes`:

            Layer 2: Planning Agent generates `steps` for execution
            for `step` in `steps`:
                
                Layer 3: Execution Agent (you) executes each given `step`

        Layer 2: Decision Agent decides whether `expected_outcome` has been satisfied
        ---

        The planning agent has already defined the following steps:
        ---
        {step_names}
        ---

        So far, you have already executed the following:
        ---
        {execution_results}
        ---

        Given this context:
        ---
        {context}
        ---

        Execute step {step_index}/{len(steps)} - {step["step"]}:
        ***
        {step["prompt"]}
        ***
        """

        response = model_manager.ask_model(
            model,
            [Message(role="user", content=prompt)],
            tools=TOOLS,
            tool_choice="auto",
        )

        if isinstance(response, str):
            return response.strip()

        for part in response:
            if part.get("type") != "function":
                continue

            function = part["function"]
            handler = TOOL_MAP.get(function["name"])
            if not handler:
                continue

            args = function["arguments"]
            if isinstance(args, str):
                args = json.loads(args)

            result = handler(**args)
            logger.info(f"🔧 Tool call executed! {function["name"]}({args["path"]})")

            context.append({
                 "function_executed": function["name"],
                 "arguements_provided": args["path"]
            })

            return result

        return ""
