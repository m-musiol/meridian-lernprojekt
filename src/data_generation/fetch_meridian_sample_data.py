"""Laedt Meridians offizielle simulierte Beispieldaten (Datenquelle 1, Stufe 1).

Pinnt den Download auf einen festen Commit-SHA von google/meridian, damit die
Referenzdaten reproduzierbar bleiben, auch wenn sich die Datei stromaufwaerts
spaeter aendert. Nutzt bewusst nur die Standardbibliothek (urllib), da pip in
diesem venv haeufig an SSL-Problemen scheitert.
"""

import argparse
import hashlib
import pathlib
import urllib.request

DEFAULT_COMMIT = "00134ea24a0f811a41ee640e89c68ed884fef0ad"
DEFAULT_FILE_PATH = "meridian/data/simulated_data/csv/geo_all_channels.csv"


def build_url(commit: str, file_path: str) -> str:
    return f"https://raw.githubusercontent.com/google/meridian/{commit}/{file_path}"


def fetch(commit: str, file_path: str, output_dir: pathlib.Path) -> pathlib.Path:
    url = build_url(commit, file_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / pathlib.Path(file_path).name

    with urllib.request.urlopen(url) as response:
        content = response.read()

    target.write_bytes(content)
    checksum = hashlib.sha256(content).hexdigest()

    print(f"Gespeichert: {target} ({len(content):,} Bytes)")
    print(f"SHA256: {checksum}")
    print(f"Quelle: {url}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Laedt Meridians offizielle simulierte Beispieldaten (Datenquelle 1)."
    )
    parser.add_argument(
        "--commit", default=DEFAULT_COMMIT, help="Gepinnter Commit-SHA in google/meridian"
    )
    parser.add_argument(
        "--file-path", default=DEFAULT_FILE_PATH, help="Pfad der Datei im meridian-Repo"
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw/meridian_sample",
        help="Zielverzeichnis fuer die heruntergeladene Datei",
    )
    args = parser.parse_args()
    fetch(args.commit, args.file_path, pathlib.Path(args.output_dir))


if __name__ == "__main__":
    main()
