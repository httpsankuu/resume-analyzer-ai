import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Resume Analyzer AI — Smart Candidate Screening",
  description:
    "AI-powered resume screening tool. Upload resumes, paste a job description, and get instant match scores using NLP — skill overlap, TF-IDF, and semantic similarity.",
  keywords: ["resume analyzer", "AI screening", "NLP", "job matching", "candidate ranking"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
