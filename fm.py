import os
import requests
import pandas as pd
import smtplib
from bs4 import BeautifulSoup
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime
import yaml
import matplotlib.pyplot as plt
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

HISTORY_PATH = "data/detected_entries.csv"
SCREENSHOT_DIR = "screenshots"

def is_new_detection(website, link, keywords):
    if os.path.exists(HISTORY_PATH):
        df_history = pd.read_csv(HISTORY_PATH)
        return not (
            (df_history["Website"] == website) &
            (df_history["Link"] == link) &
            (df_history["Keywords"] == ", ".join(sorted(set(keywords))))
        ).any()
    return True

def update_history(new_entries):
    df_new = pd.DataFrame(new_entries)
    if os.path.exists(HISTORY_PATH):
        df_existing = pd.read_csv(HISTORY_PATH)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True).drop_duplicates()
    else:
        df_combined = df_new
    df_combined.to_csv(HISTORY_PATH, index=False)

def take_screenshot(url, site_name):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    filename = f"{site_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(url, timeout=30000)
            # Aceitar cookies se botão for detectado
            if page.locator("button:has-text('Accept')").first.is_visible():
                page.locator("button:has-text('Accept')").first.click()
            elif page.locator("button:has-text('Aceitar')").first.is_visible():
                page.locator("button:has-text('Aceitar')").first.click()
            page.wait_for_timeout(2000)
            page.screenshot(path=filepath, full_page=True)
        except Exception as e:
            log(f"Erro ao capturar screenshot de {url}: {e}")
        browser.close()

    return filepath if os.path.exists(filepath) else None

load_dotenv()

EMAIL = os.getenv("EMAIL_USER")
PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP = os.getenv("SMTP_SERVER")
PORT = int(os.getenv("SMTP_PORT"))
TO = os.getenv("EMAIL_TO").split(',')

EXCEL_PATH = "data/funding_data.xlsx"
CHART_PATH = "data/funding_chart.png"
LOG_PATH = "logs/funding_log.txt"

def load_config():
    with open("scraper_config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def send_email(subject, body, attachments=[]):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = ", ".join(TO)
    msg.set_content(body)
    for filepath in attachments:
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                filename = os.path.basename(filepath)
                msg.add_attachment(f.read(), maintype="application", subtype="octet-stream", filename=filename)
    with smtplib.SMTP_SSL(SMTP, PORT) as smtp:
        smtp.login(EMAIL, PASSWORD)
        smtp.send_message(msg)

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs("logs", exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def search_keywords(text, keywords):
    return [kw for kw in keywords if kw.lower() in text.lower()]

def save_to_excel(results):
    os.makedirs("data", exist_ok=True)
    df_new = pd.DataFrame(results)
    if os.path.exists(EXCEL_PATH):
        df_old = pd.read_excel(EXCEL_PATH)
        df_combined = pd.concat([df_old, df_new], ignore_index=True).drop_duplicates()
    else:
        df_combined = df_new
    df_combined.to_excel(EXCEL_PATH, index=False)

def generate_chart():
    if os.path.exists(EXCEL_PATH):
        df = pd.read_excel(EXCEL_PATH)
        counts = df["Website"].value_counts()
        plt.figure(figsize=(10, 6))
        counts.plot(kind="bar")
        plt.title("Total of Detected Updates per Website")
        plt.xlabel("Website")
        plt.ylabel("Occurrences")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(CHART_PATH)

# ... (código anterior permanece igual)

def scrape():
    config = load_config()
    found_info = []
    checked_sites = 0

    for site in config["sites"]:
        urls = site["urls"] if "urls" in site else [site["url"]]
        deep = site.get("deep", False)
        for url in urls:
            checked_sites += 1
            try:
                try:
                    response = requests.get(url, timeout=15)
                except requests.exceptions.SSLError:
                    log(f"⚠️ SSL error on {url}, retrying without verification.")
                    response = requests.get(url, timeout=15, verify=False)

                soup = BeautifulSoup(response.text, "html.parser")
                text = soup.get_text(separator=" ")
                matches = search_keywords(text, site["keywords"])
                if matches and is_new_detection(site["name"], url, matches):
                    found_info.append({
                        "Website": site["name"],
                        "Link": url,
                        "Keywords": ", ".join(sorted(set(matches))),
                        "Date and Time": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                    log(f"✅ Match found in {site['name']}: {matches}")
                elif deep:
                    base_url = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(url))
                    internal_links = set(
                        urljoin(base_url, a["href"]) for a in soup.find_all("a", href=True)
                        if a["href"].startswith("/") or a["href"].startswith(base_url)
                    )
                    for link in list(internal_links)[:20]:
                        try:
                            sub_response = requests.get(link, timeout=15)
                        except requests.exceptions.SSLError:
                            log(f"⚠️ SSL error on deep link {link}, retrying without verification.")
                            sub_response = requests.get(link, timeout=15, verify=False)

                        sub_text = BeautifulSoup(sub_response.text, "html.parser").get_text(separator=" ")
                        sub_matches = search_keywords(sub_text, site["keywords"])
                        if sub_matches and is_new_detection(site["name"], link, sub_matches):
                            found_info.append({
                                "Website": site["name"],
                                "Link": link,
                                "Keywords": ", ".join(sorted(set(sub_matches))),
                                "Date and Time": datetime.now().strftime("%d/%m/%Y %H:%M")
                            })
                            log(f"🔎 Deep match in {site['name']}: {sub_matches}")
            except Exception as e:
                log(f"❌ Error scraping {site['name']}: {e}")
    return found_info, checked_sites

# ... (restante código permanece igual)
    config = load_config()
    found_info = []
    checked_sites = 0

    for site in config["sites"]:
        urls = site["urls"] if "urls" in site else [site["url"]]
        deep = site.get("deep", False)
        for url in urls:
            checked_sites += 1
            try:
                response = requests.get(url, timeout=15)
                soup = BeautifulSoup(response.text, "html.parser")
                text = soup.get_text(separator=" ")
                matches = search_keywords(text, site["keywords"])
                if matches and is_new_detection(site["name"], url, matches):
                    found_info.append({
                        "Website": site["name"],
                        "Link": url,
                        "Keywords": ", ".join(sorted(set(matches))),
                        "Date and Time": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                    log(f"✅ Match found in {site['name']}: {matches}")
                elif deep:
                    base_url = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(url))
                    internal_links = set(
                        urljoin(base_url, a["href"]) for a in soup.find_all("a", href=True)
                        if a["href"].startswith("/") or a["href"].startswith(base_url)
                    )
                    for link in list(internal_links)[:20]:
                        try:
                            sub_response = requests.get(link, timeout=15)
                            sub_text = BeautifulSoup(sub_response.text, "html.parser").get_text(separator=" ")
                            sub_matches = search_keywords(sub_text, site["keywords"])
                            if sub_matches and is_new_detection(site["name"], link, sub_matches):
                                found_info.append({
                                    "Website": site["name"],
                                    "Link": link,
                                    "Keywords": ", ".join(sorted(set(sub_matches))),
                                    "Date and Time": datetime.now().strftime("%d/%m/%Y %H:%M")
                                })
                                log(f"🔎 Deep match in {site['name']}: {sub_matches}")
                        except Exception as e:
                            log(f"⚠️ Error in deep scraping ({link}): {e}")
                else:
                    log(f"ℹ️ No relevant information found for {site['name']}")
            except Exception as e:
                log(f"❌ Error scraping {site['name']}: {e}")
    return found_info, checked_sites

def main():
    results, total_checked = scrape()
    attachments = [LOG_PATH]

    if results:
        save_to_excel(results)
        update_history(results)
        generate_chart()
        attachments.extend([EXCEL_PATH, CHART_PATH])

        screenshot_paths = []
        for r in results:
            screenshot = take_screenshot(r["Link"], r["Website"])
            if screenshot:
                screenshot_paths.append(screenshot)

        attachments.extend(screenshot_paths)

        body = f"{total_checked} websites were checked.\n{len(results)} contained relevant information.\n\n"
        body += "New information was found for analysis:\n\n" + "\n".join([f"{r['Website']}: {r['Link']}" for r in results])
        send_email("✅ Funding Alert: New information found", body, attachments)
        log("📧 Email sent with results.")
    else:
        body = f"{total_checked} websites were checked.\n0 contained relevant information.\n\nNo new information was detected on monitored websites."
        send_email("ℹ️ Funding Monitor: No new information found", body, attachments)
        log("📧 Email sent (no new info).")

if __name__ == "__main__":
    main()
