
from pathlib import Path
import qrcode
import qrcode.image.svg

BASE_URL = "https://rchia16.github.io/hal-openlab-2026/"

stations = {
    "00_all_stations": "",
    "01_yihao": "#yihao",
    "02_nhan": "#nhan",
    "03_shurui": "#shurui",
    "04_minh": "#minh",
    "05_yu": "#yu",
    "06_games": "#games",
}

output = Path("qr_codes")
output.mkdir(exist_ok=True)

for name, anchor in stations.items():
    url = BASE_URL.rstrip("#") + anchor

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=20,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # High-resolution PNG
    qr.make_image(
        fill_color="black",
        back_color="white"
    ).save(output / f"{name}.png")

    # Vector SVG for PowerPoint and printing
    qr.make_image(
        image_factory=qrcode.image.svg.SvgPathFillImage
    ).save(output / f"{name}.svg")

    print(f"{name}: {url}")

print("All seven QR codes generated.")

