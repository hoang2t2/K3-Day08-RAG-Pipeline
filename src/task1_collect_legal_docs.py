"""
Task 1 — Thu thập văn bản chính sách/quy định dịch vụ đại học.

Hướng dẫn:
    1. Tìm tối thiểu 3 văn bản chính sách (PDF/DOCX) từ trang công khai của một trường đại học.
    2. Tải về và lưu vào data/landing/legal/
    3. Đặt tên file rõ ràng, không dấu, mô tả đúng nội dung.

Gợi ý nguồn (ví dụ trang công khai RMIT Vietnam — rmit.edu.vn):
    - https://www.rmit.edu.vn/study-at-rmit/tuition-fees
    - https://www.rmit.edu.vn/study-at-rmit/scholarships/...
    - https://www.rmit.edu.vn/students/my-studies/fees-and-payments

Gợi ý văn bản (chủ đề dịch vụ đại học):
    - Học phí & phương thức thanh toán (Tuition Fees)
    - Chính sách học bổng (Scholarship eligibility)
    - Quy định ký túc xá / hỗ trợ chỗ ở (Accommodation Services)
    - Hướng dẫn đăng ký học phần qua cổng thông tin sinh viên (Course Registration)

Lưu ý: một số trang trường (vd VinUni, Fulbright) chặn bot crawler mặc định (HTTP 403) —
không phải lỗi của bạn, đó là cấu hình WAF/Cloudflare phía server. Đổi sang trang khác
thay vì cố vượt qua, và chỉ dùng nguồn công khai/được phép chia sẻ.
"""

from pathlib import Path
import sys

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


def setup_directory():
    """Tạo thư mục data/landing/legal/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Thư mục đã sẵn sàng: {DATA_DIR}")


# TODO: Tải file PDF/DOCX về DATA_DIR
# Có thể tải thủ công hoặc viết script download nếu có direct link.

# Ví dụ nếu có direct link:

import requests

def download_file(url: str, filename: str):
    if Path(filename).suffix.lower() not in {".pdf", ".doc", ".docx"}:
        raise ValueError("filename phải có đuôi .pdf, .doc hoặc .docx")

    filepath = DATA_DIR / filename

    response = requests.get(url, timeout = 60)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()
    if "text/html" in content_type:
        raise ValueError(
            f"URL không phải direct link tới PDF/DOCX: {url}"
            )

    filepath.write_bytes(response.content)

    if filepath.stat().st_size <= 1024:
        filepath.unlink(missing_ok=True)
        raise ValueError("File tải về rỗng hoặc quá nhỏ")

    print(f"✓ Đã tải: {filepath} ({filepath.stat().st_size:,} bytes)")
# Nếu trang là HTML thuần (không phải PDF sẵn), có thể convert nội dung text
# thành PDF đơn giản bằng thư viện fpdf2 (đã có trong requirements.txt).


if __name__ == "__main__":
    setup_directory()

download_file(
    url="https://policy.vinuni.edu.vn/wp-content/uploads/2024/05/VU_HT03.VN_QC-dao-tao-dai-hoc-he-chinh-quy-theo-he-thong-tin-chi.pdf",
    filename="Quy-che-dao-tao-dhvin.pdf",
)