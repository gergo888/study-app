import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";
import "@/styles/tokens.css";
import "@/styles/app.css";
import "@/styles/print.css";

import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin", "latin-ext"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: { default: "StudyDesk", template: "%s · StudyDesk" },
  description: "Personal learning support: summaries, flashcards, quizzes and spaced repetition.",
};

// The whole app is private and rendered in the browser behind one boundary
// (see providers.tsx), so there is no meaningful static shell to validate.
export const instant = false;

// Applies the saved theme before first paint (no light flash in dark mode).
const themeScript = `try{var t=localStorage.getItem('theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.setAttribute('data-bs-theme',t)}catch(e){}`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-bs-theme="light" className={inter.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
