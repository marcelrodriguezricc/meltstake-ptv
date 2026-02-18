import cv2
from pathlib import Path
from datetime import datetime

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera.")

    out_dir = Path(__file__).resolve().parent / "test_captures"
    out_dir.mkdir(parents=True, exist_ok=True)

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        cv2.imshow("Camera (q/Esc quit, s save)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("s"):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = out_dir / f"capture_{ts}.jpg"
            cv2.imwrite(str(path), frame)
            print(f"Saved: {path}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

