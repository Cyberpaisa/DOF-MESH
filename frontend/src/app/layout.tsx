import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "DOF Sovereign OS | Enigma #1686",
  description: "The premium dashboard for the Deterministic Observability Framework agentic ecosystem.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-black antialiased`}>
        {children}
      </body>
    </html>
  );
}
