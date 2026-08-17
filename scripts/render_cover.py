"""
render_cover.py

Собирает обложку поста: фотография + текстовая плашка поверх неё.

Картинка не генерируется нейросетью. Берётся ваше фото, поверх кладётся
свёрстанная плашка из templates/cover.html, и со страницы снимается
скриншот. Поэтому результат предсказуем: шрифты не «пляшут», текст
не расползается, а поправить отступ — это одна строка CSS.

Запуск:
    python3 scripts/render_cover.py input/photos/IMG_1.jpg \
        --title "Заголовок поста" \
        --kicker "РАЗБОР" \
        --out output/2026-08-17/cover.png
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "cover.html"

MAX_TITLE = 90
MAX_KICKER = 24


def esc(text: str) -> str:
    """Экранируем то, что подставляем в HTML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("photo", help="путь к фотографии-фону")
    ap.add_argument("--title", required=True, help="заголовок на плашке")
    ap.add_argument("--kicker", default="", help="надпись над заголовком, например рубрика")
    ap.add_argument("--handle", default="", help="подпись-юзернейм в углу")
    ap.add_argument("--out", required=True, help="куда сохранить PNG")
    args = ap.parse_args()

    photo = Path(args.photo)
    if not photo.exists():
        print(f"Фото не найдено: {photo}")
        sys.exit(1)

    if not TEMPLATE.exists():
        print(f"Не найден шаблон: {TEMPLATE}")
        sys.exit(1)

    if len(args.title) > MAX_TITLE:
        print(
            f"Заголовок длиннее {MAX_TITLE} знаков ({len(args.title)}). "
            "На плашке он не поместится — сократите."
        )
        sys.exit(1)

    if len(args.kicker) > MAX_KICKER:
        print(f"Кикер длиннее {MAX_KICKER} знаков ({len(args.kicker)}). Сократите.")
        sys.exit(1)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        page.goto(TEMPLATE.as_uri())

        # Подставляем содержимое в подготовленные элементы шаблона
        page.eval_on_selector(
            "#photo", "(el, src) => el.setAttribute('src', src)", photo.resolve().as_uri()
        )
        page.eval_on_selector("#title", "(el, v) => el.textContent = v", args.title)
        page.eval_on_selector("#kicker", "(el, v) => el.textContent = v", args.kicker)
        page.eval_on_selector("#handle", "(el, v) => el.textContent = v", args.handle)

        # Ждём, пока подгрузятся фото и веб-шрифты
        page.wait_for_function("() => document.querySelector('#photo').complete")
        page.wait_for_function("() => document.fonts.ready.then(() => true)")
        page.wait_for_timeout(300)

        page.screenshot(path=str(out))
        browser.close()

    print(f"Готово: {out}")


if __name__ == "__main__":
    main()
