import cv2
import os


def process_video(video_path):
    """
    Открытие видеофайла и плавное чтение всех кадров.
    """
    if not os.path.exists(video_path):
        print(f"Видео не найдено: {video_path}")
        return

    cap = cv2.VideoCapture(video_path)

    # Проверяем, удалось ли открыть видео
    if not cap.isOpened():
        print("Ошибка: Не удалось открыть видеофайл.")
        return

    print("Начинаю воспроизведение. Нажмите 'q' для выхода.")

    while cap.isOpened():
        ret, frame = cap.read()

        # Если кадры закончились — выходим из цикла
        if not ret:
            break

        # Показываем каждый кадр
        cv2.imshow('Parking Monitoring - Video Stream', frame)

        # Задержка 30 мс (примерно 30 кадров в секунду)
        # Если нажать 'q', цикл прервется
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cap.release()

    # Добавляем небольшую задержку перед закрытием,
    # чтобы мы успели увидеть последний кадр
    print("Видео закончилось. Нажмите любую клавишу в окне видео для закрытия.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    video_name = "new.003.028.left.avi"
    # Собираем путь к видео внутри ml_service/data/raw/
    video_path = os.path.join(current_dir, "../../data/raw/", video_name)

    process_video(video_path)