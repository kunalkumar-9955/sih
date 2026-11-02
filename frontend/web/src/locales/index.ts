import { en } from "./en";
import { hi } from "./hi";
import { as } from "./as";
import { bn } from "./bn";
import { mni } from "./mni";
import { kha } from "./kha";

export type LanguageCode = "en" | "hi" | "as" | "bn" | "mni" | "kha";

export interface LanguageOption {
  code: LanguageCode;
  name: string;
  nativeName: string;
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: "en", name: "English", nativeName: "English" },
  { code: "hi", name: "Hindi", nativeName: "हिन्दी" },
  { code: "as", name: "Assamese", nativeName: "অসমীয়া" },
  { code: "bn", name: "Bengali", nativeName: "বাংলা" },
  { code: "mni", name: "Manipuri", nativeName: "মৈতৈলোন্" },
  { code: "kha", name: "Khasi", nativeName: "Ka Ktien Khasi" },
];

export const dictionaries: Record<LanguageCode, typeof en> = {
  en,
  hi,
  as,
  bn,
  mni,
  kha,
};

export type TranslationKey = keyof typeof en;
