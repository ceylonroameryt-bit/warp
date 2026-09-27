import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ladger | Smart Commercial Accounting SaaS",
  description: "Modern, secure multi-tenant accounting platform for high-growth businesses.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-slate-950 text-slate-100 min-h-screen selection:bg-indigo-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
