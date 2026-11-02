import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/router";
import { api, User } from "../services/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isDriver: boolean;
  isAdmin: boolean;
  getDefaultPath: () => string;
}

export const getRoleDefaultPath = (role?: string): string => {
  if (role === "DRIVER") return "/driver";
  if (role === "FLEET_OPERATOR") return "/fleet";
  if (role === "SUPER_ADMIN" || role === "MINISTRY_ADMIN") return "/command-center";
  return "/command-center";
};

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
  isAuthenticated: false,
  isDriver: false,
  isAdmin: false,
  getDefaultPath: () => "/command-center",
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const router = useRouter();

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem("sih_access_token");
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const res = await api.getMe();
        setUser(res.data);
      } catch (err) {
        console.error("Auth check failed:", err);
        localStorage.removeItem("sih_access_token");
        localStorage.removeItem("sih_refresh_token");
      } finally {
        setLoading(false);
      }
    };
    initAuth();
  }, []);

  const login = async (email: string, pass: string) => {
    setLoading(true);
    try {
      const data = await api.login(email, pass);
      const access = data.data.tokens.access;
      const refresh = data.data.tokens.refresh;
      localStorage.setItem("sih_access_token", access);
      localStorage.setItem("sih_refresh_token", refresh);
      const authenticatedUser = data.data.user;
      setUser(authenticatedUser);

      const targetPath = getRoleDefaultPath(authenticatedUser.role);
      router.push(targetPath);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("sih_access_token");
    localStorage.removeItem("sih_refresh_token");
    setUser(null);
    router.push("/login");
  };

  const isDriver = user?.role === "DRIVER";
  const isAdmin = user?.role === "SUPER_ADMIN" || user?.role === "MINISTRY_ADMIN";

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        isAuthenticated: !!user,
        isDriver,
        isAdmin,
        getDefaultPath: () => getRoleDefaultPath(user?.role),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
