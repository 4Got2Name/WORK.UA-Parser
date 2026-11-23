import csv
import os
import tempfile
import unittest
from pathlib import Path

from save import save_to_csv
from work import (ParserError, get_jobs_from_files, is_blocked_page, page_url,
                  parse_jobs, parse_last_page, validate_url)

FIXTURE = Path(__file__).parent / "fixtures" / "search_page.html"
HTML = FIXTURE.read_text(encoding="utf-8")


class ParseJobsTest(unittest.TestCase):
    def setUp(self):
        self.jobs = parse_jobs(HTML)

    def test_finds_every_card(self):
        self.assertEqual(len(self.jobs), 5)

    def test_vip_card_without_salary(self):
        job = self.jobs[0]
        self.assertEqual(job.title, "RPA Developer (UIPath)")
        self.assertEqual(job.company, "Sense Bank")  # без мітки "VIP"
        self.assertEqual(job.salary, "")
        self.assertEqual(job.location, "Дистанційно")
        self.assertEqual(job.conditions, "Досвід від 2 років · Стандартний графік: 5/2")
        self.assertEqual(job.posted, "2026-11-23 18:50:01")
        self.assertEqual(job.link, "https://www.work.ua/jobs/8639857/")

    def test_salary_range_and_text(self):
        self.assertEqual(self.jobs[1].salary, "43 000 – 84 000 грн")
        self.assertEqual(self.jobs[2].salary, "Відштовхуємось від фінансових очікувань кандидата")
        self.assertEqual(self.jobs[2].company, "Bes, інжинирінгова компанія")

    def test_card_without_date_inside_defense_block(self):
        job = self.jobs[3]
        self.assertEqual(job.title, "Embedded-розробник")
        self.assertEqual(job.location, "Вся Україна")
        self.assertEqual(job.posted, "")

    def test_card_without_logo_or_badge(self):
        self.assertEqual(self.jobs[4].company, "ДСФ, ТОВ")

    def test_empty_page(self):
        self.assertEqual(parse_jobs("<html><body></body></html>"), [])


class PaginationTest(unittest.TestCase):
    def test_last_page(self):
        self.assertEqual(parse_last_page(HTML), 8)

    def test_no_pagination_means_one_page(self):
        self.assertEqual(parse_last_page("<html></html>"), 1)

    def test_page_url_keeps_other_params(self):
        self.assertEqual(page_url("https://www.work.ua/jobs-developer/?sort=salary", 3),
                         "https://www.work.ua/jobs-developer/?sort=salary&page=3")
        self.assertEqual(page_url("https://www.work.ua/jobs-developer/?page=5", 1),
                         "https://www.work.ua/jobs-developer/")


class ValidateUrlTest(unittest.TestCase):
    def test_accepts_work_ua(self):
        validate_url(" https://www.work.ua/jobs-developer/ ")

    def test_rejects_lookalike_domains(self):
        for bad in ("https://www.work.ua.evil.com/", "ftp://www.work.ua/", "work.ua/jobs"):
            with self.assertRaises(ParserError):
                validate_url(bad)


class FilesAndCsvTest(unittest.TestCase):
    def test_dedupe_and_csv(self):
        jobs = get_jobs_from_files([str(FIXTURE), str(FIXTURE)])
        self.assertEqual(len(jobs), 5)  # той самий файл двічі: без дублікатів

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.csv")
            save_to_csv(jobs, out, "ua")
            with open(out, encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0][0], "Назва вакансії")
        self.assertEqual(rows[5][1], "ДСФ, ТОВ")  # кома в назві не ламає CSV

    def test_cloudflare_page_detected(self):
        self.assertTrue(is_blocked_page('<script src="/cdn-cgi/challenge-platform/x.js"></script>'))
        self.assertFalse(is_blocked_page(HTML))


if __name__ == "__main__":
    unittest.main()
