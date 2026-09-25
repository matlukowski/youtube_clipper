const repository = "https://github.com/matlukowski/youtube_clipper";
const macDownload = `${repository}/releases/latest/download/YouTube-Clipper-macOS-arm64.dmg`;
const download = `${repository}/releases/latest/download/YouTube-Clipper-Setup.exe`;

function Mark({ className = "" }) {
  return <svg className={className} viewBox="0 0 40 40" fill="none" aria-hidden="true">
    <rect width="40" height="40" rx="11" fill="currentColor" />
    <path d="m16 11 13 9-13 9V11Z" fill="#101728" />
    <path d="M10 15h3M10 25h3" stroke="#101728" strokeWidth="2" strokeLinecap="round" />
  </svg>;
}

function Arrow({ diagonal = false }) {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d={diagonal ? "M5 19 19 5M8 5h11v11" : "M4 12h16m-6-6 6 6-6 6"} stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function DownloadIcon() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3v12m-4-4 4 4 4-4M4 17v4h16v-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function TimelineArt() {
  const frames = ["frame-one", "frame-two", "frame-three", "frame-four", "frame-five", "frame-six"];
  const bars = [12,19,13,26,35,19,28,37,20,15,25,45,34,25,38,47,26,17,29,55,42,31,17,38,48,31,22,40,51,30,45,29,18,36,43,23,19,34,47,27,16,31,37,20,12,22,30,17,10];
  return <div className="timeline-art" aria-label="Ilustracja zaznaczonego fragmentu filmu na osi czasu" role="img">
    <div className="art-heading"><span>TWÓJ MOMENT</span><span>00:30 — 01:30</span></div>
    <div className="filmstrip">
      {frames.map((frame, index) => <div className={`film-frame ${frame}`} key={frame}><span className="frame-landscape" /><span className="frame-number">0{index + 1}</span></div>)}
      <div className="selection-frame"><span className="selection-label">WYBRANY FRAGMENT</span><i className="selection-handle left" /><i className="selection-handle right" /></div>
    </div>
    <div className="ruler"><span>00:00</span><span>00:30</span><span>01:00</span><span>01:30</span><span>02:00</span></div>
    <div className="waveform" aria-hidden="true">{bars.map((height, index) => <i key={index} style={{ height: `${height}px` }} className={index >= 16 && index <= 35 ? "active" : ""} />)}</div>
    <div className="art-footer"><span className="sound-pill"><span className="sound-dot" /> Z DŹWIĘKIEM</span><span className="format-pill">MP4</span></div>
  </div>;
}

export default function Home() {
  return <>
    <div className="hero-shell" id="gora">
      <header className="site-header container">
        <a className="brand" href="#gora" aria-label="YouTube Clipper — początek strony"><Mark className="brand-mark" /><span>YouTube Clipper</span></a>
        <nav aria-label="Nawigacja główna"><a href="#jak-to-dziala">Jak to działa</a><a href="#pobierz">Pobierz</a><a href={repository} target="_blank" rel="noopener noreferrer">GitHub <span aria-hidden="true">↗</span></a></nav>
        <span className="header-platform"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 4.5 10.5 3v8H2Zm10-1.8L22 1v10H12Zm-10 10H10.5v8L2 19Zm10 0h10v10l-10-1.7Z" fill="currentColor" /></svg> Windows + macOS</span>
      </header>

      <main>
        <section className="hero container" aria-labelledby="hero-title">
          <div className="hero-copy">
            <h1 id="hero-title">Zachowaj<br /><span>najlepszy moment.</span></h1>
            <p>Wytnij fragment filmu z YouTube i zapisz go na komputerze — z dźwiękiem lub bez.</p>
            <div className="hero-actions"><a className="button button-primary" href={download}><DownloadIcon /> Pobierz na Windows <Arrow /></a><a className="button button-secondary" href={macDownload} aria-describedby="mac-requirements"><DownloadIcon /> Pobierz na macOS <Arrow /></a><a className="button button-text" href={repository} target="_blank" rel="noopener noreferrer">Zobacz na GitHubie <Arrow diagonal /></a></div>
            <p className="platform-note">macOS 15+ · Apple Silicon (M1 i nowsze)</p>
            <div className="download-meta"><span className="meta-dot" /> Darmowa aplikacja na Windows i macOS <span className="meta-divider" /> Wersja 1.1.6</div>
          </div>
          <TimelineArt />
        </section>
        <div className="hero-bottom-line container"><span>WYBIERZ FRAGMENT</span><span>ZAPISZ MP4</span><span>ZACHOWAJ NA DYSKU</span></div>
      </main>
    </div>

    <section className="how-section" id="jak-to-dziala" aria-labelledby="how-heading"><div className="container">
      <div className="section-intro"><h2 id="how-heading">Od linku do gotowego klipu.</h2><p>Trzy proste kroki w aplikacji na Twoim komputerze.</p></div>
      <ol className="steps"><li><span className="step-number">01</span><div><h3>Wklej link</h3><p>Skopiuj adres filmu lub Shorts z YouTube i otwórz go w aplikacji.</p></div></li><li><span className="step-number">02</span><div><h3>Wybierz fragment</h3><p>Ustaw początek i koniec na osi czasu lub wpisz dokładne czasy.</p></div></li><li><span className="step-number">03</span><div><h3>Zapisz na dysku</h3><p>Wybierz zapis z dźwiękiem albo bez i zachowaj klip jako MP4.</p></div></li></ol>
    </div></section>

    <section className="detail-section" aria-labelledby="detail-heading"><div className="container detail-layout"><div className="detail-graphic" aria-hidden="true"><span className="detail-line" /><span className="detail-range"><i /><i /></span><span className="detail-caption">TYLKO WYBRANY FRAGMENT</span></div><div className="detail-copy"><h2 id="detail-heading">Masz kontrolę nad tym, co zostaje.</h2><p>Przytnij dokładnie ten zakres, którego potrzebujesz. Gotowy plik MP4 trafia do folderu na Twoim komputerze.</p><div className="sound-choice"><span>DŹWIĘK</span><strong>tak <i /> nie</strong></div></div></div></section>

    <section className="download-section" id="pobierz" aria-labelledby="download-heading"><div className="container download-layout"><div><span className="download-label">YOUTUBE CLIPPER 1.1.6</span><h2 id="download-heading">Twój następny klip zaczyna się tutaj.</h2><p>Wybierz Windows 10/11 (64-bit) lub macOS 15 i nowszy. Aplikacja działa na Twoim komputerze.</p></div><div className="download-box"><a className="button button-primary" href={download}><DownloadIcon /> Pobierz na Windows <Arrow /></a><a className="button button-secondary" href={macDownload} aria-describedby="mac-requirements"><DownloadIcon /> Pobierz na macOS <Arrow /></a><p id="mac-requirements">macOS 15+ · procesory Apple (M1 i nowsze). Wersja dla Maców z Intelem nie jest dostępna.</p><a href={`${repository}/releases/latest`} target="_blank" rel="noopener noreferrer">Zobacz wydanie na GitHubie <Arrow diagonal /></a><p>Instalatory nie mają podpisu wydawcy. Windows może wyświetlić ostrzeżenie. Na Macu przeciągnij aplikację do folderu Aplikacje. Jeśli system zablokuje jej uruchomienie, użyj „Otwórz mimo to” w Ustawieniach systemowych → Prywatność i ochrona. Zawierają FFmpeg i Node.js. <a href={`${repository}/blob/main/THIRD_PARTY_NOTICES.md`} target="_blank" rel="noopener noreferrer">Licencje i źródła</a>.</p></div></div></section>

    <footer className="footer"><div className="container footer-content"><a className="brand" href="#gora"><Mark className="brand-mark" /><span>YouTube Clipper</span></a><p>Darmowa aplikacja do wycinania fragmentów filmów z YouTube.</p><a href={repository} target="_blank" rel="noopener noreferrer">GitHub <Arrow diagonal /></a></div></footer>
  </>;
}
