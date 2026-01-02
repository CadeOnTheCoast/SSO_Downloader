import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ADEM SSO Downloader",
  description: "Dashboard for managing and downloading SSO analytics data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
