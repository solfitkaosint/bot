import subprocess
import sys

def install_packages():
    packages = [
        'aiogram==3.10.0',
        'python-dotenv==1.0.0', 
        'yookassa==6.5.0',
        'Pillow==10.1.0',
        'aiofiles==23.2.1'
    ]
    
    for package in packages:
        print(f"Устанавливаю {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    print("✅ Все пакеты установлены успешно!")

if __name__ == "__main__":
    install_packages()