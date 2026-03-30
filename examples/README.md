# Integration examples

- **`github-actions-autoqa.yml`** — sample workflow that `curl`s `POST /api/run-full-test` with optional API key and webhook URL (repository secrets).

Copy the file into `.github/workflows/` in a Git repository, then add the secrets described in the workflow header.

For a quick webhook smoke test, use [https://webhook.site](https://webhook.site), paste the unique URL into `webhook_url` in the API body or into `AUTOQA_WEBHOOK_URL`, and inspect the incoming `autoqa.run.completed` JSON after a run.
