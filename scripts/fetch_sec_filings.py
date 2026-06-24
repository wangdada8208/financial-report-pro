#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


SEC_DATA = "https://data.sec.gov"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
MIN_INTERVAL_SECONDS = 0.11
LAST_REQUEST_AT = 0.0


def require_user_agent(value=None):
    user_agent = value or os.environ.get("EDGAR_USER_AGENT")
    if not user_agent:
        raise SystemExit(
            "SEC EDGAR requests require a User-Agent. Set EDGAR_USER_AGENT or pass --user-agent, "
            "for example: EDGAR_USER_AGENT='Your Name your.email@example.com'."
        )
    return user_agent


def request_json(url, user_agent):
    return json.loads(request_bytes(url, user_agent).decode("utf-8"))


def request_bytes(url, user_agent):
    global LAST_REQUEST_AT
    elapsed = time.time() - LAST_REQUEST_AT
    if elapsed < MIN_INTERVAL_SECONDS:
        time.sleep(MIN_INTERVAL_SECONDS - elapsed)
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "identity"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"SEC request failed {exc.code}: {url}") from exc
    LAST_REQUEST_AT = time.time()
    return data


def normalize_cik(cik):
    digits = re.sub(r"\D", "", str(cik or ""))
    if not digits:
        raise ValueError("Missing CIK")
    return digits.zfill(10)


def ticker_to_cik(ticker, user_agent):
    mapping = request_json(TICKER_MAP_URL, user_agent)
    target = ticker.upper()
    for row in mapping.values():
        if row.get("ticker", "").upper() == target:
            return str(row["cik_str"]).zfill(10), row.get("title")
    raise ValueError(f"Ticker not found in SEC ticker map: {ticker}")


def submissions(cik, user_agent):
    return request_json(f"{SEC_DATA}/submissions/CIK{normalize_cik(cik)}.json", user_agent)


def pick_filing(submission, filing_type):
    recent = submission.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])
    wanted = filing_type.upper()
    for idx, form in enumerate(forms):
        if form.upper() == wanted:
            return {
                "form": form,
                "accession_number": accessions[idx],
                "primary_document": primary_docs[idx],
                "filing_date": filing_dates[idx] if idx < len(filing_dates) else None,
                "report_date": report_dates[idx] if idx < len(report_dates) else None,
            }
    raise ValueError(f"No recent filing of type {filing_type} found")


def filing_url(cik, accession_number, primary_document):
    bare_cik = str(int(normalize_cik(cik)))
    accession_clean = accession_number.replace("-", "")
    return f"{SEC_ARCHIVES}/{bare_cik}/{accession_clean}/{primary_document}"


def fetch(ticker=None, cik=None, filing_type="10-K", output_dir=".", user_agent=None):
    user_agent = require_user_agent(user_agent)
    if not cik:
        cik, company_title = ticker_to_cik(ticker, user_agent)
    else:
        cik, company_title = normalize_cik(cik), None
    submission = submissions(cik, user_agent)
    filing = pick_filing(submission, filing_type)
    url = filing_url(cik, filing["accession_number"], filing["primary_document"])
    content = request_bytes(url, user_agent)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    suffix = Path(filing["primary_document"]).suffix.lower() or ".txt"
    filing_path = out / ("sec_filing.html" if suffix in {".htm", ".html"} else "sec_filing.txt")
    filing_path.write_bytes(content)

    metadata = {
        "ticker": ticker.upper() if ticker else None,
        "cik": str(int(cik)),
        "company_name": submission.get("name") or company_title,
        "filing_type": filing["form"],
        "accession_number": filing["accession_number"],
        "filing_date": filing["filing_date"],
        "report_date": filing["report_date"],
        "primary_document": filing["primary_document"],
        "source_url": url,
        "local_filing": str(filing_path),
    }
    (out / "sec_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "sec_filing_index.json").write_text(json.dumps({"selected": filing, "company": submission.get("name"), "cik": metadata["cik"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker")
    parser.add_argument("--cik")
    parser.add_argument("--filing-type", default="10-K")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--user-agent")
    args = parser.parse_args()
    if not args.ticker and not args.cik:
        raise SystemExit("Provide --ticker or --cik")
    result = fetch(args.ticker, args.cik, args.filing_type, args.output_dir, args.user_agent)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
