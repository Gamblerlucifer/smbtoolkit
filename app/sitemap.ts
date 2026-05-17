import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://smbkits.com";
  const now = new Date();

  return [
    { url: base, lastModified: now, changeFrequency: "weekly", priority: 1.0 },
    { url: `${base}/reputation-response`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: `${base}/social-presence`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${base}/local-positioning`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${base}/reputation-recovery`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${base}/brand-voice`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${base}/visibility-intelligence`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${base}/brand-responses`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
  ];
}
