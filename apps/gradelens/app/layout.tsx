import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "GradeLens — AI condition grading for used electronics",
  description:
    "Photograph a used phone or laptop and get an instant, dispute-ready condition report: defects, an A–D grade, and a resale price band.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
