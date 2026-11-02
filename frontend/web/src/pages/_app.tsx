import type { AppProps } from "next/app";
import { AuthProvider } from "../context/AuthContext";
import { ThemeProvider } from "../context/ThemeContext";
import { LanguageProvider } from "../context/LanguageContext";
import { ProtectedRoute } from "../components/ProtectedRoute";
import "../styles/globals.css";

export default function App({ Component, pageProps, router }: AppProps) {
  const isPublic = router.pathname === "/login";

  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          {isPublic ? (
            <Component {...pageProps} />
          ) : (
            <ProtectedRoute>
              <Component {...pageProps} />
            </ProtectedRoute>
          )}
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}
