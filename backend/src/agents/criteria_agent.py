# src/agents/criteria_agent.py
import logging
from typing import List

from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message

logger = logging.getLogger("uvicorn.error")


async def extract_expected_outcomes(
    query: str,
    model: Model,
    model_manager: ModelManager
) -> List[str]:

    prompt = f"""
    Given your position within a tree of agents, visualised like so:
    ---
    Layer 1: Expected Outcomes Agent (you) generates `expected_outcomes`
    for `expected_outcome` in expected_outcomes`:

        Layer 2: Planning Agent generates `steps` for execution
        for `step` in `steps`:
            
            Layer 3: Execution Agent executes each given `step`

       Layer 2: Decision Agent decides whether `expected_outcome` has been satisfied
    ---

    You are resposible for defining the `expected_outcomes` from the user's query. 
    ---
    {query}
    ---
    
    Rules:
     - List the least amount of expected outcomes required to satisfy the user's query. Each outcome you define will have its own planning agent creating a set of steps to address how to meet your outcome, so only provide the minimal amount of highest level outcomes
     - Return a simple bullet point list.
     - Do not explain.
    """

    response = model_manager.ask_model(
        model,
        [Message(role="user", content=prompt)]
    )

    text = response.strip()

    criteria = []
    for line in text.splitlines():
        line = line.strip("-• ").strip()
        if not line:
            continue
        criteria.append(line)

    if not criteria:
        logger.error("No criteria extracted, falling back to query itself")
        return [query]

    return criteria
