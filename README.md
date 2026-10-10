# Faceless YouTube Automation Starter (Hindi/Hinglish)

A configurable, cautious starter for a low-cost faceless channel. It includes topic scoring, a YouTube research script, a GitHub Actions schedule, a local OAuth bootstrap, and a minimal publishing skeleton.

**Default niche:** Hindi/Hinglish AI & technology explainers. Change it in `config/channel.yaml`.

## What this starter does today
- Collects public YouTube video search results using the YouTube Data API.
- Scores topic candidates with transparent heuristic signals (not a guarantee of virality).
- Saves a research report as JSON/CSV.
- Provides an OAuth bootstrap to authorize your own channel.
- Includes a minimal FFmpeg render pipeline for original text cards + narration.
- Includes a publishing skeleton; uploading is deliberately disabled until you explicitly configure it.
- Includes a scheduled workflow for research only.

## What it does NOT do yet
- It does not guarantee viral results, zero maintenance, or unlimited free cloud rendering.
- It does not scrape private analytics or infer competitor CTR/retention.
- It does not auto-publish publicly by default.
- It does not automatically generate reliable factual scripts from arbitrary sources. Add a vetted model/provider and a source-verification stage before production.
- Instagram/Facebook publishing is not included in the first milestone because it requires account eligibility, Meta app permissions, tokens, and a reliable public media URL.

## Quick start

1. Create a GitHub repository and upload these files.
2. In Google Cloud Console, create a project and enable **YouTube Data API v3**.
3. Create an API key for public search (restrict it to YouTube Data API v3 where possible).
4. In GitHub repository Settings → Secrets and variables → Actions, add:
   - `YOUTUBE_API_KEY`
5. Run the workflow manually (Actions → Daily topic research → Run workflow), or run locally:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   source .venv/bin/activate
   pip install -r requirements.txt
   export YOUTUBE_API_KEY="your-key"
   python -m src.research
   ```
6. Review `output/topics.json` and `output/topics.csv`.

## OAuth setup (only when ready to upload)
1. Enable YouTube Data API v3 in the same Google Cloud project.
2. Create an **OAuth Client ID → Desktop app** and download its JSON as `client_secret.json`.
3. Install requirements locally and run:
   ```bash
   python -m src.oauth_bootstrap
   ```
4. Complete Google's consent screen in your browser. The script writes `token.json`.
5. Keep `client_secret.json` and `token.json` private. Never commit them.
6. Upload workflow secrets only after reviewing the uploader:
   - `GOOGLE_OAUTH_CLIENT_JSON_B64`: base64 of `client_secret.json`
   - `GOOGLE_OAUTH_TOKEN_JSON_B64`: base64 of `token.json`
7. **Do not enable public auto-publishing yet.** Test with a private video first and verify title, description, thumbnail, and upload status.

On macOS/Linux, base64 encode a file:
```bash
base64 -w 0 client_secret.json
base64 -w 0 token.json
```
On macOS, if `-w 0` is unsupported:
```bash
base64 client_secret.json | tr -d '\\n'
base64 token.json | tr -d '\\n'
```

## Workflow design
- `research.yml`: scheduled research and artifact output only.
- Production/rendering is intentionally local/manual at first because free hosted runners have limited runtime/storage and are not a dependable 24/7 server.
- Do not put secrets in workflow logs or artifacts.

## Topic score
Each candidate gets a 0–100 heuristic score:
- Demand proxy (25): search-result view count and result count
- Freshness/momentum proxy (20): recent publication date and views
- Channel fit (20): configured keywords
- Competition opportunity (15): weaker competition gets a modest boost
- Value/originality potential (15): topic-specificity heuristic; manually verify
- Feasibility (5): enough search results to research

These are proxies, not ground truth. Competitor view counts do not reveal CTR or retention.

## Publishing safety checklist
- Use original scripts and meaningful commentary; avoid mass-produced repetitive templates.
- Use only media/music you have rights to use and keep licence/source records.
- Fact-check claims and add source links to descriptions.
- Keep `privacyStatus` set to `private` for initial tests.
- Review realistic synthetic/altered-content disclosure requirements where applicable.
- Use retries, duplicate prevention, and a manual hold for sensitive or uncertain topics.

## Next milestones
1. Validate topic discovery on 20–30 candidate topics.
2. Add a script provider and structured source verification.
3. Add licensed visuals and local FFmpeg rendering.
4. Test a private YouTube upload.
5. Add YouTube Analytics reports and feedback scoring.
6. Add Meta publishing only after account/API prerequisites are verified.

## License
Starter code: MIT-style permissive use. Dependencies and any generated media remain subject to their own licences.
