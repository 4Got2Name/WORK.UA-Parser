import csv
from dataclasses import astuple

from work import Job

HEADERS = {
    "en": ["Job Name", "Company/Organization", "Salary", "Location",
           "Conditions", "Posted", "Link"],
    "ua": ["Назва вакансії", "Компанія/Організація", "Зарплата", "Місцезнаходження",
           "Умови", "Опубліковано", "Посилання"],
}


def save_to_csv(jobs: list[Job], path: str = "parsed.csv", lang: str = "en") -> None:
    # newline="" прибирає порожні рядки між записами на Windows,
    # utf-8-sig потрібен, щоб Excel правильно показав кирилицю.
    with open(path, mode="w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(HEADERS[lang])
        for job in jobs:
            writer.writerow(astuple(job))
