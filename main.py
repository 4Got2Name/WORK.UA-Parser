import argparse
import sys

from save import save_to_csv
from work import ParserError, get_jobs, get_jobs_from_files


def parse_args():
    parser = argparse.ArgumentParser(description="Парсер вакансій work.ua у CSV")
    parser.add_argument("url", nargs="?", help="посилання на пошук, напр. https://www.work.ua/jobs-remote-developer/")
    parser.add_argument("-f", "--file", nargs="+", metavar="HTML",
                        help="розібрати збережені з браузера сторінки замість завантаження")
    parser.add_argument("-l", "--lang", choices=["en", "ua"], help="мова заголовків CSV")
    parser.add_argument("-o", "--output", default="parsed.csv", help="куди зберегти (за замовчуванням parsed.csv)")
    return parser.parse_args()


def ask_lang() -> str:
    while True:
        choice = input("Мова заголовків CSV: 1 - English, 2 - Українська: ").strip()
        if choice in ("1", "2"):
            return "en" if choice == "1" else "ua"
        print("Введіть 1 або 2.")


def main() -> int:
    args = parse_args()
    try:
        if args.file:
            jobs = get_jobs_from_files(args.file)
        else:
            url = args.url or input("Посилання на пошук work.ua: ")
            jobs = get_jobs(url)
    except ParserError as exc:
        print(f"Помилка: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nСкасовано.")
        return 1

    if not jobs:
        print("Вакансій не знайдено, файл не створено.")
        return 1

    lang = args.lang or ask_lang()
    try:
        save_to_csv(jobs, args.output, lang)
    except OSError as exc:
        print(f"Не вдалося записати {args.output}: {exc} (можливо, файл відкритий в Excel?)")
        return 1

    print(f"Готово! {len(jobs)} вакансій збережено у {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
