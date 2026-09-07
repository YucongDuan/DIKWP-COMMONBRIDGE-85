from pathlib import Path
import argparse
import webbrowser
from threading import Timer

from commonbridge85.server import serve


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8784)
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args()
    root = Path(__file__).resolve().parent
    if not args.no_browser:
        Timer(0.8, lambda: webbrowser.open(f"http://{args.host}:{args.port}")).start()
    serve(root, args.host, args.port)


if __name__ == "__main__":
    main()
