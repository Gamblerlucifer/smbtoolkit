import type { Metadata } from "next";
import { Cormorant_Garamond, DM_Sans } from "next/font/google";
import "./globals.css";

const cormorant = Cormorant_Garamond({
  variable: "--font-cormorant",
  subsets: ["latin"],
  weight: ["300", "400"],
  style: ["normal", "italic"],
  display: "swap",
});

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  weight: ["300", "400"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "SMBkits — Private Reputation Infrastructure",
    template: "%s | SMBkits",
  },
  description:
    "Private reputation management infrastructure for independent premium businesses. Brand-safe reputation management, local positioning, and social presence.",
  applicationName: "SMBkits",
  generator: "Next.js",
  category: "Business",
  classification: "Reputation Management Software",
  referrer: "origin-when-cross-origin",
  metadataBase: new URL("https://smbkits.com"),
  keywords: [
    "reputation management",
    "restaurant reputation management",
    "google review management",
    "review response management",
    "customer feedback management",
    "premium local business",
    "brand reputation protection",
    "online reputation management",
    "small business reputation management",
  ],
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
    },
  },
  openGraph: {
    siteName: "SMBkits",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
  },
  formatDetection: {
    telephone: false,
    email: false,
    address: false,
  },
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
    other: { rel: "icon", url: "/icon.png" },
  },
  manifest: "/site.webmanifest",
  verification: {
    google: "X0-9_MUtluRCoAZkR6W_JDm1MAF002oQw4i5zv3r3wo",
  },
  other: {
    "color-scheme": "dark",
  },
};

export const viewport = {
  themeColor: "#08090C",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${cormorant.variable} ${dmSans.variable}`}>
      <body>{children}</body>
    </html>
  );
}
