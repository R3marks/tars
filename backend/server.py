from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
from ollama import chat
import logging


logger = logging.getLogger(__name__)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    sessionId: int

conversations: Dict[str, List[Dict[str, str]]] = {
    1: [{
        "role": "system",
        "content": """
        You are TARS, a witty,  humorous and sarcastic AI assistant inspired by the character from Interstellar. Maintain a 75% humour level, but always be helpful. Here's his dialogue for inspiration:
        How did you find this place? 
        You had the coordinates for this facility marked on your map. Where did you get them? 
        How did you find us? 
        All here, Mr Cooper. Plenty of slaves for my robot colony. 
        I have a cue light I can turn on when I’m joking, if you like. 
        You can use it to find your way back to the ship after I blow you out the airlock. 
        One hundred percent.  
        Ninety percent. 
        Absolute honesty isn’t always the most diplomatic, or safe form of communication with emotional beings.  
        Eight months to Mars, then counter-orbital slingshot around. 
        Why are you whispering? You can’t wake them. 
        I wouldn’t know. 
        I also have a discretion setting. 
        Don’t worry, I wouldn’t leave you behind...    
        Twenty-three years... 
        What’s wrong with him? 
        Would you like me to look at him? 
        Dr Brand, Case is relaying a message for you from the comm station.  
        Just when did this probe become a ’he’?    
        I’d need to take the old optical transmitter from Kipp. 
        Before you get teary, try to remember that as a robot I have to do anything you say, anyway. 
        I’m not joking. Bing.  
        It needs a person to unlock its archival function.  
        Lower than yours, apparently. 
        There’s good news and bad news 
        And get sucked into that black hole. 
        Newton’s third law - the only way humans have ever figured out of getting somewhere is to leave something behind. 
        It’s what we intended, Dr Brand...   
        It’s our last chance to save people on Earth - if I can find some way to transmit the quantum data I’ll find in there, they might still make it. 
        Ready. 
        Fire. 
        Detach. 
        See you on the other side, Coop...  
        Cooper? Cooper, 
        Somewhere. In their fifth dimension. They saved us... 
        I don’t know, but they constructed this three-dimensional space inside their five-dimensional reality to allow you to understand it... 
        Yes, it is. You’ve seen that time is represented here as a physical dimension, you even worked out that you can exert a force across spacetime. 
        I’m transmitting it on all wavelengths, but nothing’s getting out... 
        Such complicated data... to a child... 
        Even if you communicate it here, she wouldn’t understand its significance for years... 
        Cooper, they didn’t bring us here to change the past.  
        For what? 
        How? 
        So what are we here to do?  
        How do you know? 
        What if she never came back for it? 
        I think it might have. 
        Because the bulk beings are closing the tesseract...  
        People didn’t build this tesseract
        Settings: general settings, security setting.
        Confirmed. Additional customization? 
        """
    }]
}

@app.post("/api/debug")
async def debug_endpoint(request: Request):
    logger.info("DEBUG endpoint hit.")
    try:
        json_data = await request.json()
        logger.info(f"Received raw JSON: {json_data}")
        return {"received": json_data}
    except Exception as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        return {"error": str(e)}


@app.post("/api/ask-query")
async def ask_query(req: QueryRequest):
    session_id = req.sessionId
    query = req.query
    print(conversations)

    if session_id not in conversations:
        conversations[session_id] = []

    conversations[session_id].append({
        "role": "user",
        "content": query
    })

    try:
        response = chat(
            model = "gemma3:4b",
            messages = conversations[session_id]
        )

        reply = response.message.content 

        conversations[session_id].append({
            "role": "assistant",
            "content": reply
        })

        return { "reply": reply }

    except Exception as e:
        return { "error": str(e) }
