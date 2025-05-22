import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/providers";
import { Inter } from "next/font/google";

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-inter"
});

export const metadata: Metadata = {
  title: "fucking best agent in the cloud",
  description: "fucking best agent in the cloud (fubea.cloud) is a tool for in-depth analysis and research.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link
          rel="apple-touch-icon"
          sizes="180x180"
          href="/favicon/apple-touch-icon.png"
        />
        <link
          rel="icon"
          type="image/png"
          sizes="32x32"
          href="/favicon/favicon-32x32.png"
        />
        <link
          rel="icon"
          type="image/png"
          sizes="16x16"
          href="/favicon/favicon-16x16.png"
        />
        <link rel="manifest" href="/favicon/site.webmanifest" />
      </head>
      <body className={`antialiased ${inter.variable} font-inter`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
