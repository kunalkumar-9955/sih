import React, { createContext, useContext, useEffect, useState } from "react";
import { dictionaries, LanguageCode, LanguageOption, SUPPORTED_LANGUAGES, TranslationKey } from "../locales";

interface LanguageContextType {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  t: (key: TranslationKey, fallback?: string) => string;
  languages: LanguageOption[];
}

const STORAGE_KEY = "routeiq_language";
const LEGACY_STORAGE_KEY = "northlink_language";

const LanguageContext = createContext<LanguageContextType>({
  language: "en",
  setLanguage: () => {},
  t: (key, fallback) => fallback || key,
  languages: SUPPORTED_LANGUAGES,
});

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<LanguageCode>("en");

  useEffect(() => {
    try {
      const saved = (localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY)) as LanguageCode | null;
      if (saved && dictionaries[saved]) {
        setLanguageState(saved);
      }
    } catch (e) {
      console.warn("Could not read stored language:", e);
    }
  }, []);

  const setLanguage = (newLang: LanguageCode) => {
    if (!dictionaries[newLang]) return;
    setLanguageState(newLang);
    try {
      localStorage.setItem(STORAGE_KEY, newLang);
    } catch (e) {
      console.warn("Could not persist language:", e);
    }
  };

  const t = (key: TranslationKey, fallback?: string): string => {
    const activeDict = dictionaries[language];
    if (activeDict && activeDict[key]) {
      return activeDict[key];
    }
    // Fallback to English
    if (dictionaries.en && dictionaries.en[key]) {
      return dictionaries.en[key];
    }
    return fallback || (key as string);
  };

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage,
        t,
        languages: SUPPORTED_LANGUAGES,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
