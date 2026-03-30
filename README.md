# AI Website Testing Tool

## Project Title
**AutoQA Pro**

AI Website Testing Tool for automated crawling, browser validation, issue detection, and AI-assisted insights.

## Description
AutoQA Pro is a web application that crawls websites, executes automated browser tests, detects functional and visual issues, and turns the results into actionable QA insights.

The project is built for hackathon submission and demo use. It is designed to help teams validate website behavior faster, review failures in one place, and understand what to fix next with the help of AI-generated analysis.

## Features
- Website crawling with configurable depth and page caps
- Automated browser checks across discovered pages
- Issue detection for broken flows, failed checks, and visual regressions
- AI-assisted analysis and recommendations
- Health, coverage, performance, accessibility, and security scoring
- HTML dashboard for viewing runs and results
- Run history, issue details, and page-level inspection
- PDF report generation for sharing findings
- JSON and CSV export for integration and review
- Webhook support for CI/CD style notifications

## Use Cases
- QA teams validating a staging or production-like website before release
- Developers checking for regressions after UI changes
- Product teams reviewing website health without manual test scripts
- Hackathon demos showing AI-assisted automation and reporting
- Internal teams keeping a lightweight history of scans and findings

## Tech Stack
- **Frontend:** Flask templates, HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **Browser Automation:** Selenium, webdriver-manager
- **Database:** SQLite
- **Reporting:** ReportLab, Matplotlib
- **Utilities:** Faker, JSON, CSV exports
- **AI Integration:** Configurable LLM/API analysis hooks

## Prerequisites
- **Node.js:** Not required for this repo
- **Python:** 3.10 or later recommended
- **pip:** Latest stable version recommended
- **Google Chrome:** Required for browser automation
- **Internet access:** Needed on first run for webdriver-manager and optional AI/API calls
- **Optional:** A Vercel account if you want to connect the repo for deployment

## Installation Steps

1. Clone the repository
   ```bash
   git clone https://github.com/tameemalam33/feuji_hackathon.git
   cd feuji_hackathon
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Install the browser dependencies used by Selenium
   - Make sure Google Chrome is installed
   - The first test run may download the matching driver automatically

5. Configure the environment
   - Create a `.env` file in the project root
   - Add the variables shown below

## Environment Variables
Example `.env` file only. Do not commit real keys.

```env
PORT=5000
DEBUG=1

# Database and runtime
AUTOQA_PAGE_LOAD_TIMEOUT_SEC=10
AUTOQA_MAX_DEPTH_STANDARD=2
AUTOQA_MAX_DEPTH_DEEP=3
AUTOQA_FULL_SITE_CRAWL=1
AUTOQA_CRAWL_WORKERS=3
AUTOQA_TEST_WORKERS=4
AUTOQA_CRAWL_RETRIES=2
MAX_CRAWL_PAGES=30

# Alerts and deployment
AUTOQA_API_KEY=your_api_key_here
PUBLIC_BASE_URL=http://localhost:5000
WEBHOOK_TIMEOUT_SEC=12
AUTOQA_CRITICAL_ALERT_THRESHOLD=1

# AI integration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here
LLM_API_KEY=your_optional_llm_api_key_here
```

## Run Commands

### Start the app locally
```bash
python app.py
```

### Start with a custom port
```bash
$env:PORT="8000"; python app.py
```

### Run the app in debug mode
```bash
$env:DEBUG="1"; python app.py
```

### Open the app
- Dashboard: `http://127.0.0.1:5000/dashboard`
- History: `http://127.0.0.1:5000/history`
- Reports: `http://127.0.0.1:5000/report/<run_id>`

### Useful API examples
```bash
curl http://127.0.0.1:5000/api/health
curl http://127.0.0.1:5000/api/runs/latest
```

## Render Deployment
This repository includes a [`render.yaml`](render.yaml) Blueprint for deploying the web app on Render.

### Recommended settings
- **Service type:** Web Service
- **Runtime:** Python
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
- **Health check path:** `/api/health`
- **Python version:** `3.11.11`

### Deployment steps
1. Push the repository to GitHub.
2. Connect the GitHub repo in the Render dashboard.
3. Let Render detect the `render.yaml` Blueprint, or create a web service manually.
4. Add required secrets such as `AUTOQA_API_KEY`, `OPENAI_API_KEY`, or `GROQ_API_KEY` in the Render environment settings.
5. Deploy the service and open the generated `onrender.com` URL.

### Important note
- The app can run on Render as a demo/dashboard service.
- Long Selenium scans may be slow or may exceed free-tier limits.
- If you want persistent scan history and generated files across redeploys, add a Render persistent disk and mount it for the database and output folders.

## Screenshots
Add your screenshot and video links here:

- Dashboard screenshot: `https://drive.google.com/drive/folders/1Z6uoiGOPEMMb63XjsWmStJPbv3EHenD7?usp=drive_link 
`
- Test history screenshot: `https://drive.google.com/drive/folders/1Z6uoiGOPEMMb63XjsWmStJPbv3EHenD7?usp=drive_link 
`
- Report view screenshot: `https://drive.google.com/drive/folders/1Z6uoiGOPEMMb63XjsWmStJPbv3EHenD7?usp=drive_link 
`
- Video demo link: `https://drive.google.com/drive/folders/1Z6uoiGOPEMMb63XjsWmStJPbv3EHenD7?usp=drive_link 
`

## Demo / Usage
1. Open the dashboard in your browser.
2. Enter a public website URL to test.
3. Choose crawl mode and optional page cap.
4. Start the run and wait for the scan to complete.
5. Review the run summary, issue cards, charts, and report links.

Sample/demo credentials:
- No login is required for the default local demo.
- If `AUTOQA_API_KEY` is set on the server, use `X-API-Key: <your_key>` or `Authorization: Bearer <your_key>` for protected API calls.

## Challenges & Limitations
- Long website scans can take time depending on target size and responsiveness
- Sites with CAPTCHA, authentication, or aggressive bot protection may not be fully testable
- Visual regression results depend on browser rendering and saved baselines
- SQLite is convenient for local use, but shared production workloads may need a stronger database
- AI insights depend on the quality and completeness of the captured test data
- Vercel serverless limits are not ideal for very long Selenium runs, so heavy scans are better suited to a dedicated backend host

## Future Improvements
- Add authenticated crawling support
- Improve visual diff workflows and baseline management
- Add scheduled scans and alerting
- Expand accessibility and performance auditing
- Add role-based access for team collaboration
- Improve AI summaries with trend analysis across multiple runs
- Add richer export formats such as HTML and XLSX
- Separate the long-running test worker from the web dashboard for easier cloud deployment

## Architecture Overview
```text
User enters a URL
    -> Flask dashboard sends the request to the backend
    -> QA pipeline crawls the site and discovers pages
    -> Selenium executes browser checks on each page
    -> Results are stored in SQLite
    -> AI analysis generates suggestions and insights
    -> Dashboard renders scores, issues, and downloadable reports
```
- architecture 3dview : `https://systemarc.vercel.app/`


### Simple Flow Explanation
- The **dashboard** captures the target URL and scan options.
- The **backend** orchestrates crawling, checks, and report generation.
- The **automation layer** runs browser tests and collects screenshots, metrics, and failures.
- The **database** stores scan history, page audits, and test results.
- The **AI layer** converts raw failures into concise, actionable guidance.

## Submission Notes
- Generated files such as `instance/`, `__pycache__/`, virtual environments, screenshots, and PDFs are intentionally excluded from commits.
- The repository is meant to stay clean and easy to review before submission.
- Screenshots and video evidence should be linked from Drive in the section above.

