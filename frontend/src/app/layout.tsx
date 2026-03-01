import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SRTI Friction Risk Map",
  description: "Real-time Swedish road friction risk map"
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
