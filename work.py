"""Завантаження і розбір сторінок пошуку вакансій work.ua.

Модуль нічого не робить під час імпорту: ні input(), ні запитів.
"""

import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.work.ua"
ALLOWED_HOSTS = {"work.ua", "www.work.ua"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
}
TIMEOUT = 20          # секунд на один запит
DELAY = 1.0           # пауза між сторінками, щоб не навантажувати сайт
MAX_PAGES = 100       # запобіжник від нескінченного циклу


class ParserError(Exception):
    """Помилка, яку можна зрозуміло показати користувачу."""


class BlockedError(ParserError):
    """Сайт повернув захисну сторінку (Cloudflare) замість вакансій."""


@dataclass
class Job:
    title: str
    company: str
    salary: str
    location: str
    conditions: str
    posted: str
    link: str


# ---------- URL ----------

def validate_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
        raise ParserError("Це не посилання на work.ua (очікую https://www.work.ua/...)")
    return url


def page_url(url: str, page: int) -> str:
    """Підставляє ?page=N, не ламаючи інші параметри запиту."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if page <= 1:
        query.pop("page", None)
    else:
        query["page"] = [str(page)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


# ---------- Мережа ----------

def fetch(url: str, session: requests.Session) -> str:
    try:
        response = session.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise ParserError(f"Не вдалося завантажити {url}: {exc}") from exc

    if response.headers.get("cf-mitigated") == "challenge" or response.status_code == 403:
        raise BlockedError(
            "work.ua (Cloudflare) заблокував автоматичний запит. "
            "Збережіть сторінку з браузера (Ctrl+S) і запустіть парсер з --file."
        )
    if response.status_code != 200:
        raise ParserError(f"Сайт відповів кодом {response.status_code} на {url}")

    response.encoding = "utf-8"
    return response.text


# ---------- Розбір HTML ----------

def _clean(text: str) -> str:
    # split() прибирає і звичайні, і нерозривні/тонкі пробіли (\xa0,  )
    return " ".join(text.split())


def _field(card, icon: str) -> str:
    """Текст поля, позначеного іконкою glyphicon-<icon> (компанія, зарплата, адреса...)."""
    icon_tag = card.select_one(f"span.glyphicon-{icon}")
    if icon_tag is None:
        return ""
    value = icon_tag.find_next_sibling("span")
    return _clean(value.get_text(" ")) if value else ""


def parse_job(card) -> Job | None:
    title_link = card.select_one("h2 a[href]")
    if title_link is None:
        return None  # не картка вакансії (реклама тощо)

    time_tag = card.find("time")
    return Job(
        title=_clean(title_link.get_text()),
        company=_field(card, "company"),
        salary=_field(card, "hryvnia-fill"),
        location=_field(card, "map-marker"),
        conditions=_field(card, "list"),
        posted=time_tag.get("datetime", "") if time_tag else "",
        link=urljoin(BASE_URL, title_link["href"]),
    )


def parse_jobs(html: str) -> list[Job]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for card in soup.select("div.job-link"):
        job = parse_job(card)
        if job:
            jobs.append(job)
    return jobs


def parse_last_page(html: str) -> int:
    """Номер останньої сторінки з пагінації; якщо пагінації немає, то 1."""
    soup = BeautifulSoup(html, "html.parser")
    pages = [1]
    for link in soup.select("ul.pagination a[href]"):
        values = parse_qs(urlparse(link["href"]).query).get("page", [])
        pages += [int(v) for v in values if v.isdigit()]
    return max(pages)


def is_blocked_page(html: str) -> bool:
    return "cdn-cgi/challenge-platform" in html and "job-link" not in html


# ---------- Збирання всіх сторінок ----------

def _dedupe(jobs: list[Job]) -> list[Job]:
    # Нові вакансії зсувають сторінки під час парсингу, тож можливі дублікати
    seen, result = set(), []
    for job in jobs:
        if job.link not in seen:
            seen.add(job.link)
            result.append(job)
    return result


def get_jobs(url: str, delay: float = DELAY) -> list[Job]:
    url = validate_url(url)
    with requests.Session() as session:
        first = fetch(url, session)
        last_page = min(parse_last_page(first), MAX_PAGES)
        print(f"Знайдено сторінок: {last_page}")

        jobs = parse_jobs(first)
        print(f"Сторінка 1: {len(jobs)} вакансій")

        for page in range(2, last_page + 1):
            time.sleep(delay)
            page_jobs = parse_jobs(fetch(page_url(url, page), session))
            print(f"Сторінка {page}: {len(page_jobs)} вакансій")
            if not page_jobs:
                break
            jobs += page_jobs

    return _dedupe(jobs)


def get_jobs_from_files(paths: list[str]) -> list[Job]:
    jobs = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                html = f.read()
        except OSError as exc:
            raise ParserError(f"Не вдалося прочитати файл {path}: {exc}") from exc
        if is_blocked_page(html):
            raise BlockedError(f"{path} містить сторінку захисту Cloudflare, а не вакансії")
        page_jobs = parse_jobs(html)
        print(f"{path}: {len(page_jobs)} вакансій")
        jobs += page_jobs
    return _dedupe(jobs)
