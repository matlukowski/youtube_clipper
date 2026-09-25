# YouTube Clipper

Darmowa aplikacja na Windows i macOS do wycinania wybranego fragmentu filmu z YouTube. Zapisuje MP4 na dysku, z dźwiękiem lub bez.

## Pobieranie

Pobierz instalator dla swojego komputera:

- [Windows 10/11 x64](https://github.com/matlukowski/youtube_clipper/releases/latest/download/YouTube-Clipper-Setup.exe)
- [macOS 15+ — Apple Silicon (M1 i nowsze)](https://github.com/matlukowski/youtube_clipper/releases/latest/download/YouTube-Clipper-macOS-arm64.dmg)
- [macOS 15+ — Intel](https://github.com/matlukowski/youtube_clipper/releases/latest/download/YouTube-Clipper-macOS-x86_64.dmg)

Wszystkie pliki są również na [stronie wydań](https://github.com/matlukowski/youtube_clipper/releases).

Instalator jest przeznaczony dla Windows 10/11 x64. Nie jest podpisany cyfrowo, dlatego Windows może wyświetlić ostrzeżenie przy uruchamianiu.

Na Macu otwórz DMG i przeciągnij aplikację do folderu Aplikacje. Uruchom ją z tego folderu. Wydanie macOS ma lokalny podpis ad-hoc, ale nie ma certyfikatu Developer ID ani notaryzacji Apple. Jeśli macOS zablokuje pierwsze uruchomienie, po próbie otwarcia użyj **Ustawienia systemowe → Prywatność i ochrona → Otwórz mimo to**. Nie wyłączaj zabezpieczeń całego systemu. Typ procesora sprawdzisz w menu Apple → Ten Mac.

Wersja macOS zawiera Python, FFmpeg oraz Node.js; nie wymaga Homebrew ani instalowania zależności. Klipy i ustawienia trafiają do `~/Library/Application Support/YouTube Clipper/`. Folder zapisu można zmienić w aplikacji.

Instalatory zawierają FFmpeg i Node.js. Informacje licencyjne oraz źródła odpowiadających wersji FFmpeg są w [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) i zasobach wydania.

## Jak działa

1. Wklej link do publicznego filmu lub Shorts na YouTube.
2. Wybierz początek i koniec fragmentu.
3. Wybierz, czy MP4 ma zawierać dźwięk, i zapisz klip na dysku.

Obsługiwane są publiczne, zakończone filmy. Dostępność pobierania zależy także od YouTube i danego materiału.

## Landing page

Strona promocyjna działa w Next.js i jest gotowa do wdrożenia na Vercel. Aplikacja do wycinania działa lokalnie na Windows i macOS; landing page nie wykonuje montażu w przeglądarce.

```powershell
npm install
npm run dev
```

Otwórz `http://localhost:3000`. Przed wdrożeniem możesz ustawić `NEXT_PUBLIC_SITE_URL` na produkcyjny adres strony, aby linki podglądu w mediach społecznościowych wskazywały właściwą domenę. Na Vercel adres produkcyjny jest też odczytywany z `VERCEL_PROJECT_PRODUCTION_URL`.

## Budowanie aplikacji Windows

Kod wersji desktopowej jest w [`desktop/`](desktop/). Wymaga Pythona 3.12+, Node.js, FFmpeg i Inno Setup 6. Z katalogu `desktop/` utwórz środowisko `.venv`, a następnie uruchom `build-desktop.ps1`. Skrypt dołącza wymagane narzędzia do instalatora. Gotowy plik powstaje jako `desktop/dist/YouTube-Clipper-Setup.exe`.

Instalator i jego zależności należy zweryfikować przed redystrybucją. Wydanie GitHub zawiera plik binarny; nie jest on przechowywany w historii Git.

## Budowanie aplikacji macOS z Windowsa

Workflow [`macos-release.yml`](.github/workflows/macos-release.yml) buduje aplikację na natywnych runnerach GitHub: `macos-15` (arm64) i `macos-15-intel` (x86_64). Można go uruchomić ręcznie w zakładce Actions. Wyniki są artefaktami przebiegu; publikacja w Releases następuje dopiero po sprawdzeniu obu wyników.

Skrypt [`desktop/build-macos.sh`](desktop/build-macos.sh) kompiluje FFmpeg 8.0 i x264 z przypiętych źródeł, dołącza Node.js 22.17.0 z weryfikacją SHA-256, uruchamia testy Pythona i JavaScript, a następnie buduje `.app` i `.dmg`. Wymaga macOS 15+, Pythona 3.12, narzędzi Xcode, nasm i pkgconf oraz zależności z `requirements-desktop.txt` i `requirements-dev.txt`.

Test gotowego `.app` działa z PATH ograniczonym do narzędzi systemowych. Otwiera natywne okno Cocoa, ładuje edytor i most Python–JavaScript, sprawdza dołączone Node.js i yt-dlp oraz eksportuje próbny MP4 z dźwiękiem i bez. Raport `smoke.json` jest dołączony do artefaktów. Testy nie gwarantują pobrania każdego filmu z YouTube ani zachowania Gatekeepera na każdym komputerze użytkownika.
