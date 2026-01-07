import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SSO Downloader",
  description: "Dashboard for managing and downloading Sanitary Sewer Overflow (SSO) analytics data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased" suppressHydrationWarning>{children}</body>
    </html>
  );
}
