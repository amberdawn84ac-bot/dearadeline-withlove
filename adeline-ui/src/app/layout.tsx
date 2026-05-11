import type { Metadata } from "next";
import {
  Inter,
  Kalam,
  Kranky,
  Permanent_Marker,
  Swanky_and_Moo_Moo,
} from "next/font/google";
import localFont from 'next/font/local';
import Script from "next/script";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

// Handwritten body — warm, personal, like a note from a friend
const kalam = Kalam({
  variable: "--font-kalam",
  weight: ["400", "700"],
  subsets: ["latin"],
});

// Playful headers — fun facts, asides, unexpected delights
const kranky = Kranky({
  variable: "--font-kranky",
  weight: "400",
  subsets: ["latin"],
});

// Emphasis — key terms, warnings, things that must be remembered
const permanentMarker = Permanent_Marker({
  variable: "--font-permanent-marker",
  weight: "400",
  subsets: ["latin"],
});

// Body alt — casual, conversational tone
const swankyAndMooMoo = Swanky_and_Moo_Moo({
  variable: "--font-swanky",
  weight: "400",
  subsets: ["latin"],
});

// Load Emilys Candy locally to avoid Turbopack issues
const emilysCandy = localFont({
  src: '../fonts/EmilysCandy-Regular.ttf',
  variable: "--font-emilys-candy",
  weight: "400",
  display: 'swap',
});

export const metadata: Metadata = {
  title: "Dear Adeline Academy — Education as Unique as Your Child",
  description: "An AI-powered homeschool learning companion that adapts to your student's interests, tracks skills toward graduation, and transforms curiosity into achievement.",
  icons: {
    icon: '/adeline-nav.png',
    apple: '/adeline-nav.png',
  },
  openGraph: {
    title: 'Dear Adeline Academy',
    description: 'Oklahoma homeschooling reimagined. AI-powered, student-led, standards-aligned.',
    images: [{ url: '/og-image.jpg', width: 1200, height: 630 }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      {/*
        Patch customElements.define to be idempotent before any third-party
        scripts (e.g. Vercel toolbar) load. Without this guard, scripts that
        call define() more than once — or that are injected by both the app
        and the Vercel platform — throw "already been defined" errors.
      */}
      <Script id="custom-elements-guard" strategy="beforeInteractive">{`
        (function () {
          var _define = window.customElements.define.bind(window.customElements);
          window.customElements.define = function (name, constructor, options) {
            if (!window.customElements.get(name)) {
              _define(name, constructor, options);
            }
          };
        })();
      `}</Script>
      <body
        className={`${inter.variable} ${emilysCandy.variable} ${kalam.variable} ${kranky.variable} ${permanentMarker.variable} ${swankyAndMooMoo.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
