"""
PWA 아이콘 자동 생성 스크립트
512x512 PNG 이미지를 여러 크기로 자동 변환
"""
from PIL import Image, ImageDraw, ImageFont
import os

# 아이콘 크기 목록
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

# 출력 디렉토리
OUTPUT_DIR = "static/icons"

def create_output_dir():
    """출력 디렉토리 생성"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"✅ 디렉토리 생성: {OUTPUT_DIR}")

def create_base_icon(size=512):
    """
    기본 아이콘 생성 (512x512)
    실제 로고가 있다면 이 함수 대신 이미지 파일을 사용하세요
    """
    # 배경 그라데이션
    img = Image.new('RGB', (size, size), color='white')
    draw = ImageDraw.Draw(img)
    
    # 그라데이션 배경 (초록색)
    for i in range(size):
        # 상단: 밝은 초록 #4CAF50, 하단: 어두운 초록 #2E7D32
        r = int(76 - (76 - 46) * i / size)
        g = int(175 - (175 - 125) * i / size)
        b = int(80 - (80 - 50) * i / size)
        draw.rectangle([(0, i), (size, i + 1)], fill=(r, g, b))
    
    # 원형 배경
    circle_margin = size // 8
    circle_bbox = [circle_margin, circle_margin, size - circle_margin, size - circle_margin]
    draw.ellipse(circle_bbox, fill='white')
    
    # 아이콘 텍스트 (📱 또는 QR)
    try:
        # 이모지 폰트 사용 시도
        font_size = size // 3
        font = ImageFont.truetype("seguiemj.ttf", font_size)  # Windows 이모지 폰트
        text = "📱"
    except:
        # 폰트 로드 실패 시 텍스트 사용
        font_size = size // 4
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        text = "QR"
    
    # 텍스트 중앙 정렬
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2 - bbox[1]
    
    draw.text((text_x, text_y), text, fill='#4CAF50', font=font)
    
    return img

def resize_icon(base_image, size):
    """아이콘 크기 조정"""
    resized = base_image.resize((size, size), Image.Resampling.LANCZOS)
    return resized

def generate_icons(source_image=None):
    """
    모든 크기의 아이콘 생성
    
    Args:
        source_image: 소스 이미지 경로 (선택). None이면 자동 생성
    """
    create_output_dir()
    
    # 기본 이미지 로드 또는 생성
    if source_image and os.path.exists(source_image):
        print(f"📁 소스 이미지 로드: {source_image}")
        base_img = Image.open(source_image)
        
        # 정사각형이 아니면 중앙 크롭
        if base_img.width != base_img.height:
            print("⚠️  이미지가 정사각형이 아닙니다. 중앙 크롭합니다.")
            min_dimension = min(base_img.width, base_img.height)
            left = (base_img.width - min_dimension) // 2
            top = (base_img.height - min_dimension) // 2
            base_img = base_img.crop((left, top, left + min_dimension, top + min_dimension))
        
        # 512x512로 리사이즈
        if base_img.width != 512:
            base_img = base_img.resize((512, 512), Image.Resampling.LANCZOS)
    else:
        print("🎨 기본 아이콘 생성 중...")
        base_img = create_base_icon()
    
    # 512x512 원본 저장
    output_path = os.path.join(OUTPUT_DIR, "icon-512x512.png")
    base_img.save(output_path, "PNG", quality=100)
    print(f"✅ 생성: icon-512x512.png")
    
    # 나머지 크기 생성
    for size in ICON_SIZES:
        if size == 512:
            continue
        
        resized = resize_icon(base_img, size)
        output_path = os.path.join(OUTPUT_DIR, f"icon-{size}x{size}.png")
        resized.save(output_path, "PNG", quality=100)
        print(f"✅ 생성: icon-{size}x{size}.png")
    
    # 파비콘 생성 (16x16, 32x32)
    for size in [16, 32]:
        resized = resize_icon(base_img, size)
        output_path = os.path.join(OUTPUT_DIR, f"favicon-{size}x{size}.png")
        resized.save(output_path, "PNG", quality=100)
        print(f"✅ 생성: favicon-{size}x{size}.png")
    
    print("\n🎉 모든 아이콘 생성 완료!")
    print(f"📂 위치: {OUTPUT_DIR}/")
    print("\n다음 단계:")
    print("1. manifest.json의 아이콘 경로 확인")
    print("2. index.html의 아이콘 링크 확인")
    print("3. 앱 테스트")

def create_splash_screen():
    """스플래시 스크린 이미지 생성 (선택 사항)"""
    width, height = 1080, 1920  # 일반적인 모바일 화면 비율
    
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # 그라데이션 배경
    for i in range(height):
        r = int(102 + (118 - 102) * i / height)
        g = int(126 + (76 - 126) * i / height)
        b = int(234 + (162 - 234) * i / height)
        draw.rectangle([(0, i), (width, i + 1)], fill=(r, g, b))
    
    # 로고 (중앙)
    logo_size = 300
    logo = create_base_icon(logo_size)
    logo_x = (width - logo_size) // 2
    logo_y = (height - logo_size) // 2 - 100
    img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)
    
    # 텍스트
    try:
        title_font = ImageFont.truetype("malgun.ttf", 60)
        sub_font = ImageFont.truetype("malgun.ttf", 30)
    except:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
    
    title = "로보그램 QR출석"
    subtitle = "잠시만 기다려주세요..."
    
    # 제목
    bbox = draw.textbbox((0, 0), title, font=title_font)
    text_width = bbox[2] - bbox[0]
    text_x = (width - text_width) // 2
    text_y = logo_y + logo_size + 50
    draw.text((text_x, text_y), title, fill='white', font=title_font)
    
    # 부제목
    bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    text_width = bbox[2] - bbox[0]
    text_x = (width - text_width) // 2
    text_y = text_y + 80
    draw.text((text_x, text_y), subtitle, fill='rgba(255,255,255,0.8)', font=sub_font)
    
    output_path = os.path.join(OUTPUT_DIR, "splash-1080x1920.png")
    img.save(output_path, "PNG", quality=100)
    print(f"✅ 스플래시 스크린 생성: splash-1080x1920.png")

if __name__ == "__main__":
    print("=" * 50)
    print("📱 PWA 아이콘 생성기")
    print("=" * 50)
    print()
    
    # 옵션 선택
    print("옵션을 선택하세요:")
    print("1. 기본 아이콘 자동 생성")
    print("2. 내 이미지 파일 사용")
    print()
    
    choice = input("선택 (1 또는 2): ").strip()
    
    if choice == "2":
        image_path = input("이미지 파일 경로를 입력하세요 (예: logo.png): ").strip()
        if not os.path.exists(image_path):
            print(f"❌ 파일을 찾을 수 없습니다: {image_path}")
            print("기본 아이콘을 생성합니다.")
            generate_icons()
        else:
            generate_icons(image_path)
    else:
        generate_icons()
    
    # 스플래시 스크린 생성 여부
    print()
    create_splash = input("스플래시 스크린도 생성하시겠습니까? (y/n): ").strip().lower()
    if create_splash == 'y':
        create_splash_screen()
    
    print("\n✨ 완료!")
