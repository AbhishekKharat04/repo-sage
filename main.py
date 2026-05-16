from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from analyzer import RepoAnalyzer
from generators import (
    gen_dockerfile, gen_compose, gen_kubernetes,
    gen_cicd, gen_aws_terraform, gen_monitoring, gen_env_and_nginx
)
import uvicorn

app = FastAPI(title="ShipSage", description="AI DevOps Pipeline Generator — powered by IBM watsonx")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

templates = Jinja2Templates(directory="templates")


class AnalyzeRequest(BaseModel):
    repo_url: str
    watsonx_api_key: str = ""
    watsonx_project_id: str = ""


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze")
async def analyze_repo(data: AnalyzeRequest):
    try:
        analyzer = RepoAnalyzer(data.watsonx_api_key, data.watsonx_project_id)
        analysis = await analyzer.analyze(data.repo_url)

        stack = analysis["stack"]
        ptype = analysis["project_type"]
        files = analysis.get("all_files", [])

        return {
            **analysis,
            "dockerfile": gen_dockerfile(stack, ptype, files),
            "compose": gen_compose(stack, files),
            "kubernetes": gen_kubernetes(stack, ptype),
            "cicd": gen_cicd(stack, files),
            "aws_terraform": gen_aws_terraform(stack, files),
            "monitoring": gen_monitoring(stack),
            "env_config": gen_env_and_nginx(stack, files),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ShipSage", "engine": "IBM watsonx Granite"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
