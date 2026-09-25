# YouTube Clipper

Darmowa aplikacja na Windows do wycinania wybranego fragmentu filmu z YouTube. Zapisuje MP4 na dysku, z dźwiękiem lub bez.

## Pobieranie

Pobierz [najnowszy instalator Windows](https://github.com/matlukowski/youtube_clipper/releases/latest/download/YouTube-Clipper-Setup.exe) albo przejdź do [strony wydań](https://github.com/matlukowski/youtube_clipper/releases).

Instalator jest przeznaczony dla Windows 10/11 x64. Nie jest podpisany cyfrowo, dlatego Windows może wyświetlić ostrzeżenie przy uruchamianiu.

Instalator zawiera FFmpeg (GPLv3) i Node.js. Informacje licencyjne oraz źródło odpowiadającej wersji FFmpeg są w [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) i zasobach wydania.

## Jak działa

1. Wklej link do publicznego filmu lub Shorts na YouTube.
2. Wybierz początek i koniec fragmentu.
3. Wybierz, czy MP4 ma zawierać dźwięk, i zapisz klip na dysku.

Obsługiwane są publiczne, zakończone filmy. Dostępność pobierania zależy także od YouTube i danego materiału.

## Landing page

Strona promocyjna działa w Next.js i jest gotowa do wdrożenia na Vercel. Aplikacja do wycinania działa lokalnie na Windows; landing page nie wykonuje montażu w przeglądarce.

```powershell
npm install
npm run dev
```

Otwórz `http://localhost:3000`. Przed wdrożeniem możesz ustawić `NEXT_PUBLIC_SITE_URL` na produkcyjny adres strony, aby linki podglądu w mediach społecznościowych wskazywały właściwą domenę. Na Vercel adres produkcyjny jest też odczytywany z `VERCEL_PROJECT_PRODUCTION_URL`.

## Budowanie aplikacji Windows

Kod wersji desktopowej jest w [`desktop/`](desktop/). Wymaga Pythona 3.12+, Node.js, FFmpeg i Inno Setup 6. Z katalogu `desktop/` utwórz środowisko `.venv`, a następnie uruchom `build-desktop.ps1`. Skrypt dołącza wymagane narzędzia do instalatora. Gotowy plik powstaje jako `desktop/dist/YouTube-Clipper-Setup.exe`.

Instalator i jego zależności należy zweryfikować przed redystrybucją. Wydanie GitHub zawiera plik binarny; nie jest on przechowywany w historii Git.
