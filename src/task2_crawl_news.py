"""
Task 2 — Crawl bài viết/thông báo về dịch vụ đại học.

Hướng dẫn:
    1. Crawl tối thiểu 5 bài viết từ trang công khai của một trường đại học.
    2. Sử dụng Crawl4AI hoặc thư viện crawling tương tự.
    3. Lưu output vào data/landing/news/
    4. Mỗi bài lưu 1 file JSON với metadata (url, title, date_crawled, content).

Cài đặt:
    pip install crawl4ai
    playwright install chromium   # bắt buộc — pip install crawl4ai KHÔNG tự tải browser binary,
                                   # thiếu bước này sẽ báo lỗi
                                   # "BrowserType.launch: Executable doesn't exist"

Gợi ý chủ đề: thông báo tuyển sinh, sự kiện, dịch vụ thư viện, hỗ trợ sinh viên, học bổng.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"


def setup_directory():
    """Tạo thư mục data/landing/news/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# Nguồn: VinUni — chuyên mục Tin nổi bật (https://vinuni.edu.vn/vi/category/tin-noi-bat/)
ARTICLE_URLS = [
    "https://vinuni.edu.vn/vi/vingroup-tang-toc-dao-tao-20-000-nhan-tai-ai-thuc-chien/",
    "https://vinuni.edu.vn/vi/nghien-cuu-he-gen-nguoi-viet-toan-dien-nhat-duoc-cong-bo-tren-nature-communications/",
    "https://vinuni.edu.vn/vi/vinuni-ket-noi-cong-dong-khoa-hoc-viet-nam-toan-cau-kieu-hoi-tri-thuc-cho-dat-nuoc/",
    "https://vinuni.edu.vn/vi/hoc-quan-tri-kinh-doanh-can-gioi-mon-gi-hoc-o-dau-chat-luong/",
    "https://vinuni.edu.vn/vi/vinuni-vinh-du-nhan-giai-vang-quoc-te-ve-trach-nhiem-xa-hoi-va-phat-trien-ben-vung/",
]


async def crawl_article(url: str) -> dict:
    """
    Crawl một bài viết và trả về dict chứa metadata + content.

    Returns:
        {
            "url": str,
            "title": str,
            "date_crawled": str (ISO format),
            "content_markdown": str
        }
    """
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        if not result.success:
            raise RuntimeError(f"Crawl thất bại cho {url}: {result.error_message}")

        title = (result.metadata or {}).get("title") or url
        return {
            "url": url,
            "title": title,
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": result.markdown,
        }


async def crawl_all():
    """Crawl toàn bộ bài viết trong ARTICLE_URLS.

    1 URL lỗi không được chặn các URL còn lại — bắt lỗi từng bài để tối đa hoá
    số bài crawl thành công (test chỉ yêu cầu tối thiểu 5 file, không phải 100%).
    """
    setup_directory()

    saved, failed = 0, 0
    for i, url in enumerate(ARTICLE_URLS, 1):
        print(f"[{i}/{len(ARTICLE_URLS)}] Crawling: {url}")
        try:
            article = await crawl_article(url)
        except Exception as e:
            print(f"  ✗ Lỗi: {e}")
            failed += 1
            continue

        # Lưu file JSON
        filename = f"article_{i:02d}.json"
        filepath = DATA_DIR / filename
        filepath.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ Saved: {filepath}")
        saved += 1

    print(f"\nHoàn tất: {saved} thành công, {failed} lỗi (tổng {len(ARTICLE_URLS)} URL).")


if __name__ == "__main__":
    if not ARTICLE_URLS:
        print("⚠ Hãy điền ARTICLE_URLS trước khi chạy!")
        print("Gợi ý: tìm trang thông báo/sự kiện trên trang chính thức của trường đại học")
    else:
        asyncio.run(crawl_all())
