import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";
import { CandidateProfileProvider } from "@/components/profile/CandidateProfileProvider";
import { AuthProvider } from "@/components/auth/AuthProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Road2Hire",
  description: "AI-powered career readiness platform",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full overflow-x-hidden bg-background text-foreground antialiased">
        <AuthProvider>
          <CandidateProfileProvider>
            <Sidebar />
            <main className="min-h-screen bg-background text-foreground md:pl-64">
              {children}
            </main>
          </CandidateProfileProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
