import asyncio
import uvicorn

if __name__ == "__main__":
    if hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=3001,
        reload=False,  # 🚫 Don't use reload here
    )
