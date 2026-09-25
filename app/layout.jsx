import "@fontsource/manrope/400.css";
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";
import "@fontsource/manrope/800.css";
import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL
  || (process.env.VERCEL_PROJECT_PRODUCTION_URL && `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`)
  || (process.env.VERCEL_URL && `https://${process.env.VERCEL_URL}`)
  || "http://localhost:3000";

export const metadata = {
  metadataBase: new URL(siteUrl),
  title: "YouTube Clipper — zachowaj najlepszy moment",
  description: "Darmowa aplikacja na Windows i macOS do wycinania fragmentów filmów z YouTube. Wybierz zakres i zapisz MP4 na dysku — z dźwiękiem lub bez.",
  openGraph: {
    title: "YouTube Clipper — zachowaj najlepszy moment",
    description: "Wytnij fragment filmu z YouTube i zapisz go na komputerze — z dźwiękiem lub bez.",
    type: "website",
    locale: "pl_PL",
    siteName: "YouTube Clipper"
  },
  twitter: { card: "summary_large_image" },
  robots: { index: true, follow: true }
};

export default function RootLayout({ children }) {
  return <html lang="pl"><body>{children}</body></html>;
}
