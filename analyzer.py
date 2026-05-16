import httpx
import base64
import re
import time
from typing import Optional

# Files/folders to skip during analysis
SKIP_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
    '.woff', '.woff2', '.ttf', '.eot', '.otf',
    '.mp4', '.mp3', '.wav', '.pdf', '.zip', '.tar',
    '.gz', '.exe', '.dll', '.so', '.pyc', '.pyo',
    '.lock', '.min.js', '.min.css', '.map'
}

SKIP_FOLDERS = {
    'node_modules', '.git', '__pycache__', 'dist',
    'build', '.next', 'venv', 'env', '.venv',
    '.idea', '.vscode', 'coverage', '.pytest_cache',
    '.tox', '.mypy_cache', '.eggs', 'vendor'
}

PRIORITY_FILES = {
    'main.py', 'app.py', 'index.js', 'index.ts', 'app.js',
    'server.js', 'server.ts', 'index.html', 'main.go',
    'app.ts', 'manage.py', 'package.json', 'requirements.txt',
    'README.md', 'Dockerfile', 'docker-compose.yml',
    'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
    'Makefile', 'setup.py', 'pyproject.toml', '.env.example',
    'config.py', 'settings.py', 'urls.py', 'routes.py'
}

MAX_FILE_CHARS = 2500
MAX_FILES_TO_READ = 15
MAX_CONTEXT_CHARS = 8000


class RepoAnalyzer:
    def __init__(self, api_key: str = "", project_id: str = ""):
        self.api_key = api_key.strip()
        self.project_id = project_id.strip()
        self.watsonx_url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"

    def parse_repo_url(self, url: str):
        """Extract owner and repo name from a GitHub URL."""
        url = url.strip().rstrip('/')
        pattern = r'github\.com/([^/]+)/([^/\s]+?)(?:\.git)?(?:[/?#].*)?$'
        match = re.search(pattern, url)
        if not match:
            raise ValueError("Invalid GitHub URL. Use format: https://github.com/owner/repo")
        return match.group(1), match.group(2)

    def should_skip(self, path: str) -> bool:
        """Check if a file should be skipped during analysis."""
        parts = path.lower().split('/')
        for part in parts[:-1]:
            if part in SKIP_FOLDERS:
                return True
        filename = parts[-1]
        if filename.startswith('.'):
            return True
        ext = ''
        if '.' in filename:
            ext = '.' + filename.rsplit('.', 1)[-1].lower()
        if ext in SKIP_EXTENSIONS:
            return True
        return False

    async def get_repo_tree(self, owner: str, repo: str):
        """Fetch the complete file tree from a GitHub repository."""
        async with httpx.AsyncClient(timeout=30) as client:
            for branch in ['main', 'master', 'dev', 'develop']:
                resp = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
                    headers={"Accept": "application/vnd.github.v3+json"}
                )
                if resp.status_code == 200:
                    return resp.json().get('tree', []), branch
        raise Exception("Could not fetch repository. Make sure it's a public GitHub repo.")

    async def get_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        """Fetch the content of a single file from GitHub."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            if resp.status_code == 200:
                data = resp.json()
                size = data.get('size', 0)
                if size > 100000:  # skip files > 100KB
                    return f"[File too large: {size} bytes]"
                raw = data.get('content', '')
                if raw:
                    decoded = base64.b64decode(raw).decode('utf-8', errors='ignore')
                    return decoded[:MAX_FILE_CHARS]
        return None

    async def get_iam_token(self) -> Optional[str]:
        """Get an IBM Cloud IAM token for watsonx API access."""
        if not self.api_key:
            return None
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                'https://iam.cloud.ibm.com/identity/token',
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data=f'grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={self.api_key}'
            )
            if resp.status_code == 200:
                return resp.json().get('access_token')
        return None

    async def call_watsonx(self, prompt: str) -> str:
        """Call IBM watsonx Granite model for AI-powered analysis."""
        token = await self.get_iam_token()
        if not token or not self.project_id:
            return None  # Will trigger fallback

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self.watsonx_url,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                json={
                    "model_id": "ibm/granite-13b-instruct-v2",
                    "input": prompt,
                    "parameters": {
                        "decoding_method": "greedy",
                        "max_new_tokens": 600,
                        "stop_sequences": ["###", "---END---"]
                    },
                    "project_id": self.project_id
                }
            )
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                if results:
                    return results[0].get('generated_text', '').strip()
        return None

    def detect_stack(self, file_list: list, file_contents: dict) -> list:
        """Detect the technology stack from file list and contents."""
        stack = []
        content_str = str(file_contents).lower()

        # Languages
        if any(f.endswith('.py') for f in file_list): stack.append("Python")
        if any(f.endswith('.js') for f in file_list): stack.append("JavaScript")
        if any(f.endswith('.ts') or f.endswith('.tsx') for f in file_list): stack.append("TypeScript")
        if any(f.endswith('.go') for f in file_list): stack.append("Go")
        if any(f.endswith('.java') for f in file_list): stack.append("Java")
        if any(f.endswith('.rs') for f in file_list): stack.append("Rust")
        if any(f.endswith('.rb') for f in file_list): stack.append("Ruby")
        if any(f.endswith('.php') for f in file_list): stack.append("PHP")
        if any(f.endswith('.cs') for f in file_list): stack.append("C#")
        if any(f.endswith('.cpp') or f.endswith('.c') for f in file_list): stack.append("C/C++")

        # Frameworks
        if 'django' in content_str: stack.append("Django")
        if 'fastapi' in content_str: stack.append("FastAPI")
        if 'flask' in content_str: stack.append("Flask")
        if 'express' in content_str: stack.append("Express.js")
        if any('next.config' in f for f in file_list): stack.append("Next.js")
        if 'react' in content_str: stack.append("React")
        if 'vue' in content_str: stack.append("Vue.js")
        if 'angular' in content_str: stack.append("Angular")
        if 'spring' in content_str: stack.append("Spring Boot")
        if 'rails' in content_str: stack.append("Ruby on Rails")

        # Infra & Tools
        if any('Dockerfile' in f for f in file_list): stack.append("Docker")
        if any('docker-compose' in f for f in file_list): stack.append("Docker Compose")
        if any('.github/workflows' in f for f in file_list): stack.append("GitHub Actions")
        if any('package.json' in f for f in file_list): stack.append("npm")
        if any('requirements.txt' in f or 'pyproject.toml' in f for f in file_list): stack.append("pip")
        if any('.env' in f for f in file_list): stack.append("Environment Config")

        return stack if stack else ["Unknown"]

    def detect_project_type(self, file_list: list, stack: list) -> str:
        """Determine the type of project (web app, API, CLI, library, etc.)."""
        has_html = any(f.endswith('.html') for f in file_list)
        has_api = any(keyword in str(file_list).lower() for keyword in ['api', 'routes', 'endpoints', 'views'])
        has_cli = any(keyword in str(file_list).lower() for keyword in ['cli', 'command', '__main__'])
        has_tests = any('test' in f.lower() for f in file_list)

        if any(fw in stack for fw in ['React', 'Vue.js', 'Angular', 'Next.js']):
            return "Web Application (Frontend)"
        elif any(fw in stack for fw in ['Django', 'FastAPI', 'Flask', 'Express.js', 'Spring Boot']):
            return "Web Application (Full-Stack)" if has_html else "Backend API"
        elif has_html:
            return "Static Website"
        elif has_cli:
            return "CLI Tool"
        elif has_api:
            return "API Service"
        else:
            return "Software Library"

    def generate_architecture(self, file_list: list) -> str:
        """Generate a text-based architecture diagram from file structure."""
        # Group files by top-level directory
        dirs = {}
        root_files = []
        for f in file_list:
            parts = f.split('/')
            if len(parts) == 1:
                root_files.append(f)
            else:
                top_dir = parts[0]
                if top_dir not in dirs:
                    dirs[top_dir] = []
                dirs[top_dir].append('/'.join(parts[1:]))

        arch = "```\n"
        arch += "📦 Repository Root\n"
        for f in sorted(root_files)[:8]:
            arch += f"├── 📄 {f}\n"
        for d, files in sorted(dirs.items()):
            arch += f"├── 📁 {d}/  ({len(files)} files)\n"
            for f in sorted(files)[:3]:
                arch += f"│   ├── {f}\n"
            if len(files) > 3:
                arch += f"│   └── ... +{len(files)-3} more\n"
        arch += "```"
        return arch

    def generate_fallback_analysis(self, owner: str, repo: str, file_list: list, file_contents: dict) -> dict:
        """Smart rule-based analysis when watsonx is not configured."""
        stack = self.detect_stack(file_list, file_contents)
        project_type = self.detect_project_type(file_list, stack)
        stack_str = ", ".join(stack)

        priority_found = [f for f in file_list if any(pf in f.split('/')[-1] for pf in PRIORITY_FILES)]
        architecture = self.generate_architecture(file_list)

        # Detect interesting patterns
        has_tests = any('test' in f.lower() for f in file_list)
        has_ci = any('.github/workflows' in f or 'Jenkinsfile' in f for f in file_list)
        has_docker = any('Dockerfile' in f or 'docker-compose' in f for f in file_list)
        has_docs = any('docs/' in f or 'documentation/' in f.lower() for f in file_list)

        summary = f"""## What This Project Does

**{owner}/{repo}** is a **{project_type}** built with **{stack_str}**.

The repository contains **{len(file_list)} files** organized across {len(set(f.split('/')[0] for f in file_list if '/' in f))} directories. \
{"It includes a test suite for reliability. " if has_tests else ""}\
{"CI/CD pipelines automate deployment. " if has_ci else ""}\
{"Docker support enables containerized deployment. " if has_docker else ""}

### Architecture Overview
{architecture}

> 💡 *Connect your IBM watsonx API key above for a deeper, AI-powered analysis with Granite.*"""

        # Entry point detection
        entry_points = []
        for f in file_list:
            name = f.split('/')[-1].lower()
            if name in ['main.py', 'app.py', 'index.js', 'index.ts', 'server.js', 'main.go', 'manage.py']:
                entry_points.append(f)

        starting_guide = f"""## Your Onboarding Roadmap

### Step 1 — Understand the Purpose
Read the `README.md` first. It tells you what this project does and how to set it up.

### Step 2 — Find the Entry Point
{"The main entry point is: **`" + entry_points[0] + "`**. Start reading here." if entry_points else "Look for files named `main.*`, `app.*`, `index.*`, or `server.*` — these are entry points."}

### Step 3 — Understand the Data Flow
Trace how data moves through the app:
1. **Input** — Where does user/data come in? (API routes, CLI args, file input)
2. **Processing** — What business logic transforms the data?
3. **Output** — Where does the result go? (database, API response, file, UI)

### Step 4 — Check Dependencies
{"Review `package.json` for npm packages." if any('package.json' in f for f in file_list) else ""}\
{"Review `requirements.txt` for Python packages." if any('requirements.txt' in f for f in file_list) else ""}\
{"Review `go.mod` for Go modules." if any('go.mod' in f for f in file_list) else ""}

### Step 5 — Run It Locally
Follow the README setup instructions. If none exist, look for a `Makefile`, `docker-compose.yml`, or scripts in a `scripts/` folder.

### ⚠️ What NOT to Touch (Yet)
- Config files (`.env`, `config.*`, `settings.*`) — changing these can break everything
- Database migrations — modifying these can corrupt data
- CI/CD pipelines — breaking these blocks the whole team

> 💡 *Add your IBM watsonx credentials for personalized onboarding guidance.*"""

        critical_files = "## Critical Files You Must Know\n\n"
        critical_files += "| File | Role | Priority |\n|------|------|----------|\n"
        for f in priority_found[:8]:
            name = f.split('/')[-1]
            if name == 'README.md':
                critical_files += f"| `{f}` | Project documentation & setup | 🔴 Read First |\n"
            elif name in ['main.py', 'app.py', 'index.js', 'server.js', 'index.ts', 'main.go']:
                critical_files += f"| `{f}` | Application entry point | 🔴 Critical |\n"
            elif name in ['package.json', 'requirements.txt', 'go.mod', 'Cargo.toml']:
                critical_files += f"| `{f}` | Dependency manifest | 🟡 Important |\n"
            elif name in ['Dockerfile', 'docker-compose.yml']:
                critical_files += f"| `{f}` | Container configuration | 🟡 Important |\n"
            elif name in ['config.py', 'settings.py', '.env.example']:
                critical_files += f"| `{f}` | Configuration | ⚠️ Handle With Care |\n"
            else:
                critical_files += f"| `{f}` | Key project file | 🟢 Review |\n"
        if not priority_found:
            for f in file_list[:5]:
                critical_files += f"| `{f}` | Project file | 🟢 Review |\n"
        critical_files += "\n> 💡 *Connect IBM watsonx for detailed file-by-file analysis.*"

        danger_zones = f"""## Danger Zones — Handle With Care

### 🔴 High Risk
- **Configuration files** (`.env`, `config.*`, `settings.*`) — contain secrets and environment-specific values. NEVER commit these to git.
- **Database migrations** — modifying existing migrations can corrupt production data. Always create NEW migrations.
- **Authentication/Authorization code** — `auth.*`, `middleware.*`, JWT handlers — bugs here = security vulnerabilities.

### 🟡 Medium Risk
- **Files with 200+ lines** — these are often tightly coupled and hard to refactor safely
- **Files imported by 5+ other files** — changing these creates cascade failures
- **Third-party integrations** — API keys, webhook handlers, payment logic

### 🟢 Safe to Explore
- Test files (`test_*`, `*_test.*`, `*.spec.*`)
- Documentation files
- Static assets (CSS, images)
- Example/sample files

### 📊 Repo Health Indicators
| Metric | Status |
|--------|--------|
| Has Tests | {"✅ Yes" if has_tests else "❌ No"} |
| Has CI/CD | {"✅ Yes" if has_ci else "❌ No"} |
| Has Docker | {"✅ Yes" if has_docker else "❌ No"} |
| Has Docs | {"✅ Yes" if has_docs else "❌ No"} |
| Total Files | {len(file_list)} |

> 💡 *Add your IBM watsonx API key for repo-specific risk analysis.*"""

        readme = f"""# {repo}

## Overview
{repo} is a {project_type.lower()} built with {stack_str}.

## Tech Stack
{chr(10).join(f'- {s}' for s in stack)}

## Project Structure
{architecture}

## Getting Started

### Prerequisites
{chr(10).join(f'- {s}' for s in stack[:3])}

### Installation
1. Clone the repository
   ```bash
   git clone https://github.com/{owner}/{repo}.git
   cd {repo}
   ```
2. Install dependencies
3. Configure environment variables
4. Run the application

## Key Files
{chr(10).join(f'- `{f}`' for f in priority_found[:7]) if priority_found else '- See repository'}

## Contributing
1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m "feat: add amazing feature"`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License
See the LICENSE file for details.

---
*Generated by [RepoSage](https://github.com/AbhishekKharat04/repo-sage) — AI-powered repository onboarding*"""

        return {
            "summary": summary,
            "starting_guide": starting_guide,
            "critical_files": critical_files,
            "danger_zones": danger_zones,
            "readme": readme,
            "ai_powered": False
        }

    async def analyze(self, repo_url: str) -> dict:
        """Main analysis pipeline — fetches repo, analyzes files, generates onboarding guide."""
        start_time = time.time()
        owner, repo = self.parse_repo_url(repo_url)

        # Fetch file tree
        tree, branch = await self.get_repo_tree(owner, repo)

        # Filter files
        all_files = [
            f['path'] for f in tree
            if f['type'] == 'blob' and not self.should_skip(f['path'])
        ]

        # Prioritize important files
        priority = [f for f in all_files if any(pf in f.split('/')[-1] for pf in PRIORITY_FILES)]
        others = [f for f in all_files if f not in priority]
        ordered_files = (priority + others)[:MAX_FILES_TO_READ]

        # Fetch file contents
        file_contents = {}
        for path in ordered_files:
            content = await self.get_file_content(owner, repo, path)
            if content:
                file_contents[path] = content

        file_list_str = '\n'.join(all_files)
        code_context = '\n\n'.join(
            [f"=== {p} ===\n{c}" for p, c in list(file_contents.items())[:10]]
        )[:MAX_CONTEXT_CHARS]

        # Detect stack for metadata
        stack = self.detect_stack(all_files, file_contents)
        project_type = self.detect_project_type(all_files, stack)

        # Try watsonx AI analysis
        ai_powered = bool(self.api_key and self.project_id)

        if ai_powered:
            summary = await self.call_watsonx(f"""You are a senior software engineer. Analyze this GitHub repository.

Repository: {owner}/{repo}
Files:
{file_list_str[:2000]}

Code:
{code_context[:3000]}

Write a clear, structured analysis:
1. What this project does (2-3 sentences)
2. Tech stack used (list each technology)
3. Who would use it and why
4. Architecture overview (how the pieces fit together)

Use markdown formatting with headers and bullet points.

###""")

            starting_guide = await self.call_watsonx(f"""You are onboarding a new developer to {owner}/{repo}.

Files:
{file_list_str[:1500]}

Code:
{code_context[:2000]}

Write a "New Developer Starting Guide" in markdown:
- Which file to read first and why
- The main flow of the application (step by step)
- Top 3 things to understand before touching code
- What NOT to touch as a beginner
- How to run the project locally

###""")

            critical_files = await self.call_watsonx(f"""Analyze this repository: {owner}/{repo}

Files:
{file_list_str[:1500]}

Code:
{code_context[:2000]}

Create a markdown table listing 5-7 critical files. For each:
- File path
- What it does (one sentence)
- Risk level (High/Medium/Low)
- Why it matters

###""")

            danger_zones = await self.call_watsonx(f"""Analyze {owner}/{repo} for risks and complexity.

Files:
{file_list_str[:1500]}

Code:
{code_context[:2000]}

Identify danger zones in markdown:
- Complex or risky files (with specific file names)
- Tightly coupled code areas
- Technical debt indicators
- Things that could break easily
- Security concerns

###""")

            readme = await self.call_watsonx(f"""Generate a professional README.md for {owner}/{repo}.

Files: {file_list_str[:1000]}
Code: {code_context[:2000]}

Write a complete README with these sections:
# {repo}
## Overview
## Tech Stack  
## Getting Started
## Project Structure
## Contributing

Use proper markdown formatting.

###""")

            # If any watsonx call failed, use fallback for that section
            if not all([summary, starting_guide, critical_files, danger_zones, readme]):
                fallback = self.generate_fallback_analysis(owner, repo, all_files, file_contents)
                summary = summary or fallback["summary"]
                starting_guide = starting_guide or fallback["starting_guide"]
                critical_files = critical_files or fallback["critical_files"]
                danger_zones = danger_zones or fallback["danger_zones"]
                readme = readme or fallback["readme"]
        else:
            fallback = self.generate_fallback_analysis(owner, repo, all_files, file_contents)
            summary = fallback["summary"]
            starting_guide = fallback["starting_guide"]
            critical_files = fallback["critical_files"]
            danger_zones = fallback["danger_zones"]
            readme = fallback["readme"]

        elapsed = round(time.time() - start_time, 1)

        return {
            "repo": f"{owner}/{repo}",
            "branch": branch,
            "total_files": len(all_files),
            "analyzed_files": len(file_contents),
            "all_files": all_files,
            "ai_powered": ai_powered,
            "stack": stack,
            "project_type": project_type,
            "analysis_time": elapsed,
            "summary": summary,
            "starting_guide": starting_guide,
            "critical_files": critical_files,
            "danger_zones": danger_zones,
            "readme": readme
        }
