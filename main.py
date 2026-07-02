import os
import httpx
from fastapi import FastAPI, HTTPException

from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="YouTrack Connector")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/youtrack/issues/{issue_id}")
async def get_issue(issue_id: str):
    async with httpx.AsyncClient(timeout=20) as client:
        resq = await client.get(f"{os.getenv('YOUTRACK_URL')}/api/issues/{issue_id}",
            params={"fields": "summary,description,assignee(id,login,fullName,email)"
            },
            headers={"Authorization": f"Bearer {os.getenv('YOUTRACK_TOKEN')}"
                     }
         )
        if resq.status_code != 200:
         raise HTTPException(status_code=resq.status_code, detail=resq.text)
        
        return resq.json()