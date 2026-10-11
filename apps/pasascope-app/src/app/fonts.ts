import { Noto_Sans, Noto_Sans_Thai, Prompt } from "next/font/google";

// Downloaded at build time and served from this origin, so the browser never
// contacts Google and the fonts satisfy `font-src 'self'`.

/** Reading face for Thai text: body copy, forms, tables and transcripts. */
export const notoSansThai = Noto_Sans_Thai({
  subsets: ["thai", "latin"],
  display: "swap",
  variable: "--font-noto-thai",
});

/** Latin companion to the Thai reading face. */
export const notoSans = Noto_Sans({
  subsets: ["latin"],
  style: ["normal", "italic"],
  display: "swap",
  variable: "--font-noto",
});

/** Display face for headings and large numerals only. */
export const prompt = Prompt({
  subsets: ["thai", "latin"],
  weight: ["500", "600", "700"],
  display: "swap",
  variable: "--font-prompt",
});

export const fontVariables = `${notoSansThai.variable} ${notoSans.variable} ${prompt.variable}`;
