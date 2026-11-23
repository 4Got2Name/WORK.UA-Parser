# WORK.UA Parser

Collects jobs from every page of a work.ua search and saves them to CSV
(title, company, salary, location, conditions, date posted, link).

**This started as a result of the Udemy course I'm completing.**

## Install

```
pip install -r requirements.txt
```

## Usage

```
python main.py https://www.work.ua/jobs-remote-developer/ --lang ua
```

work.ua sits behind Cloudflare and often blocks scripted requests (HTTP 403).
In that case open the search in a browser, save each page with Ctrl+S, and parse the files:

```
python main.py --file page1.html page2.html --lang ua -o result.csv
```

Run tests: `python -m unittest`
