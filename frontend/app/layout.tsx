import type { Metadata } from "next";
import { Geist } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Trading Bot",
  description: "Plateforme de trading automatisé",
};

const navLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/strategies", label: "Stratégies" },
  { href: "/backtest", label: "Backtesting" },
  { href: "/scan", label: "Scanner" },
  { href: "/optimize", label: "Optimiser" },
  { href: "/logs", label: "Logs" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className={`${geist.className} bg-gray-950 text-gray-100 min-h-screen`}>
        <nav className="border-b border-gray-800 px-6 py-4 flex items-center gap-8">
          <span className="font-bold text-lg text-emerald-400">Trading Bot</span>
          {navLinks.map((l) => (
            <Link key={l.href} href={l.href} className="text-gray-400 hover:text-white transition-colors text-sm">
              {l.label}
            </Link>
          ))}
        </nav>
        <main className="p-6">{children}</main>
      </body>
    </html>
  );
}
