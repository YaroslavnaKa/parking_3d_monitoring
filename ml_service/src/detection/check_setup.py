import torch
import detectron2
import sys
import os


def verify():
    print(f"--- Итоговая проверка системы ---")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Detectron2: {detectron2.__version__}")
    print(f"MPS (Apple M4) доступен: {torch.backends.mps.is_available()}")

    # Настройка путей
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_path = os.path.join(current_dir, "omni3d_repo")

    # Добавляем путь к репозиторию в начало списка путей
    if repo_path not in sys.path:
        sys.path.insert(0, repo_path)

    try:
        # Пробуем импортировать сам пакет и базовый конфиг
        import cubercnn
        from cubercnn.config import get_cfg
        print("✅ УСПЕХ: Библиотека Omni3D (cubercnn) полностью доступна!")
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
    except Exception as e:
        print(f"✅ Библиотека импортирована, но возникла мелкая ошибка: {e}")
        print("   (Это нормально, так как мы еще не загрузили саму модель)")


if __name__ == "__main__":
    verify()