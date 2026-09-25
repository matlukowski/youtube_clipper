# Narzędzia dołączone do instalatora

## FFmpeg — Windows

Instalator zawiera `ffmpeg.exe` w wersji `8.0-essentials_build-www.gyan.dev`, zbudowany z opcjami `--enable-gpl --enable-version3`. Jest udostępniany na warunkach GPLv3. Tekst licencji i informacje o konfiguracji pochodzą z tej samej dystrybucji i znajdują się w `desktop/third_party/` oraz w katalogu instalacji aplikacji.

Autor dystrybucji wskazuje źródło FFmpeg: [commit `140fd653ae`](https://github.com/FFmpeg/FFmpeg/commit/140fd653ae). Archiwum źródła jest dołączone do [wydania 1.1.6](https://github.com/matlukowski/youtube_clipper/releases/tag/v1.1.6) jako `ffmpeg-source-140fd653ae.zip`.

Informacje o licencji FFmpeg: [FFmpeg License and Legal Considerations](https://www.ffmpeg.org/legal.html).

## Node.js

Instalator zawiera `node.exe` w wersji 22.17.0. Tekst licencji i informacje o komponentach zewnętrznych z oficjalnego wydania Node.js znajdują się w `desktop/third_party/Node-LICENSE.txt` oraz w katalogu instalacji aplikacji.

## FFmpeg, x264 i Node.js — macOS

Paczki macOS zawierają FFmpeg 8.0 ([commit `140fd653aed8cad774f991ba083e2d01e86420c7`](https://github.com/FFmpeg/FFmpeg/commit/140fd653aed8cad774f991ba083e2d01e86420c7)) z biblioteką x264 ([commit `c24e06c2e184345ceb33eb20a15d1024d9fd3497`](https://github.com/mirror/x264/commit/c24e06c2e184345ceb33eb20a15d1024d9fd3497)). Ta konfiguracja jest objęta GPLv2 lub nowszą (`--enable-gpl`, bez `--enable-version3`). Nie zawiera bibliotek wykonawczych Homebrew.

Kompletne archiwa użytych źródeł są dostępne obok instalatorów jako `ffmpeg-macos-source.tar.gz` i `x264-macos-source.tar.gz`. Skrypt odtwarzający kompilację to [`desktop/build-macos.sh`](desktop/build-macos.sh). Kopia skryptu, konfiguracja FFmpeg i teksty licencji znajdują się wewnątrz aplikacji w `Contents/Resources/third_party`.

Node.js 22.17.0 pochodzi z oficjalnej paczki dla Darwin arm64. Suma SHA-256 jest sprawdzana podczas budowania, a plik LICENSE tej dystrybucji jest dołączony do aplikacji. Oficjalne archiwum wydania: https://nodejs.org/dist/v22.17.0/.
