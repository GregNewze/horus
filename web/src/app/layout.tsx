import type { Metadata } from "next";
import { Inter_Tight, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const display = Inter_Tight({ variable: "--f-display", subsets: ["latin"], weight: ["500", "600", "700"] });
const body = Inter({ variable: "--f-body", subsets: ["latin"] });
const mono = JetBrains_Mono({ variable: "--f-mono", subsets: ["latin"], weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "Hórus · consórcio contra contas laranja",
  description: "Cooperativas e fintechs pequenas juntam suspeitas fracas, pseudonimizadas, e acham redes de contas laranja no Pix que nenhuma acharia sozinha.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className={`${display.variable} ${body.variable} ${mono.variable}`}>{children}</body>
    </html>
  );
}
