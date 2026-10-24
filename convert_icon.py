import os
from PIL import Image

def generate_icons_from_favicon_dir(favicon_dir="favicon_io"):
    candidate_files = [
        "android-chrome-512x512.png",
        "android-chrome-192x192.png",
        "apple-touch-icon.png",
        "favicon-32x32.png"
    ]
    
    source_path = None
    for filename in candidate_files:
        full_path = os.path.join(favicon_dir, filename)
        if os.path.exists(full_path):
            source_path = full_path
            break

    if not source_path:
        print(f"Bỏ qua: Không tìm thấy file PNG phù hợp trong '{favicon_dir}/'")
        return

    print(f"Đang tạo icon từ: {source_path}")
    img = Image.open(source_path)

    # Xuất icon.ico cho Windows
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save("icon.ico", format="ICO", sizes=ico_sizes)

    # Xuất icon.icns cho macOS
    icns_sizes = [(16, 16), (32, 32), (48, 48), (128, 128), (256, 256), (512, 512)]
    img.save("icon.icns", format="ICNS", sizes=icns_sizes)
    print("✓ Tạo icon.ico và icon.icns thành công.")

if __name__ == "__main__":
    generate_icons_from_favicon_dir()