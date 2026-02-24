import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VulnSentinel - Security Audit Platform",
  description: "AI-powered automated code auditing and remediation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>{children}</body>
    </html>
  );
}
