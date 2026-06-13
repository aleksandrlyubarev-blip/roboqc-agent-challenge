import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "DepositShield — draft a rental condition report",
  description:
    "Photograph a rental at move-in or move-out and get a structured condition report that organizes visual evidence and classifies normal wear vs. damage. Not legal advice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
