import type { Metadata } from "next";
import { Providers } from "./Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "NeuroGrid — Smart Neighbourhood Power Grid",
  description: "Live simulation console for an RL-optimized smart neighbourhood power grid: solar, battery, EV chargers, and AI agent decisions in real time.",
  authors: [{ name: "NeuroGrid" }],
  openGraph: {
    title: "NeuroGrid — Smart Grid Console",
    description: "Real-time simulation of a smart neighbourhood grid with reinforcement learning energy optimization.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "NeuroGrid",
    description: "Smart Neighbourhood Power Grid Simulation.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" type="image/svg+xml" href="/logo.svg" />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
