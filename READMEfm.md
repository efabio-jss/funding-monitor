# Funding Monitor – Web Scraper & Alert System

This Python tool automatically monitors selected websites related to **renewable energy funding** and **government grants** , searching for new updates and sending email alerts with structured reports and screenshots.

---

## ✅ Key Features

- Loads a `.yaml` configuration of monitored sites and keywords
- Supports **deep crawling** for internal links
- Detects new relevant information using keyword matching
- Tracks historical detections to avoid duplicates
- Takes automatic screenshots via Playwright
- Generates:
  - Excel report
  - Detection history log
  - Bar chart of keyword hits per website
- Sends results via email with all files attached

---

## 🔧 Requirements

- Python 3.8+
- JavaScript-enabled browser (Playwright uses Chromium)
- Install dependencies:
```bash
pip install -r requirements.txt
playwright install


📁 Configuration Files

scraper_config.yaml

sites:
  - name: "Funding Portal"
    url: "https://example.com/funding"
    keywords: ["solar", "battery", "renewable", "grant"]
    deep: true
  - name: "Government Energy"
    urls:
      - "https://gov.uk/energy-updates"
      - "https://gov.uk/green-grants"
    keywords: ["bess", "pv", "storage", "subsidy"]


.env

EMAIL_USER=your_email@example.com
EMAIL_PASSWORD=your_password_or_app_token
SMTP_SERVER=smtp.example.com
SMTP_PORT=465
EMAIL_TO=recipient1@example.com,recipient2@example.com


🖥️ How It Works

Loads configuration from .yaml
Crawls and scans selected websites
Identifies new info based on keyword match

Saves:

Excel with detections
Log file
Screenshot (Playwright)
Chart of frequency per website
Sends email with attachments


🧠 Use Cases
Monitor government & institutional sites for new funding calls
Track energy policy pages or grant portals
Use in PM, Business Dev, or Regulatory Strategy teams


📌 Notes
All results stored under data/, logs/ and screenshots/
Duplicate entries are skipped automatically (based on URL + keywords)
Playwright ensures compatibility with dynamic content

