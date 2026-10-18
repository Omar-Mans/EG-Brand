import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "EG Brand Studio", description: "Arabic-first brand and content platform" };

const FONTS =
  "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&family=Readex+Pro:wght@400;500;600;700" +
  "&family=Reem+Kufi:wght@400;700&family=Cairo:wght@400;700;900&family=Tajawal:wght@400;700;900&family=El+Messiri:wght@400;700" +
  "&family=Lalezar&family=Amiri:wght@400;700&family=Changa:wght@400;700&family=Almarai:wght@400;700;800&family=Aref+Ruqaa:wght@400;700" +
  "&family=Rakkas&family=DM+Sans:wght@400;700&family=Playfair+Display:wght@400;700&family=Montserrat:wght@400;700" +
  "&family=Cormorant+Garamond:wght@500;700&display=swap";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <head>
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link rel="stylesheet" href={FONTS} />
      </head>
      <body>{children}</body>
    </html>
  );
}
