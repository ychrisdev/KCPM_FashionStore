import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { auth } from "../api/client";

export interface AuthUser {
  username: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  id?: number;
  role?: string;
  can_access_admin?: boolean;
  is_admin?: boolean;
  avatar?: string | null;
}

interface AuthContextType {
  user: AuthUser | null;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const setUser = useCallback((u: AuthUser | null) => {
    setUserState(u);
  }, []);

  const logout = useCallback(async () => {
    try {
      await auth.logout();
    } catch (err) {
      console.log(err);
    }

    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_role");

    setUserState(null);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    auth
      .getCurrentUser()
      .then(
        (data: {
          username?: string;
          email?: string;
          first_name?: string;
          last_name?: string;
          id?: number;
          role?: string;
          can_access_admin?: boolean;
          is_admin?: boolean;
          avatar?: string | null;
        }) => {
          if (data.role) {
            localStorage.setItem("user_role", data.role);
          } else {
            localStorage.removeItem("user_role");
          }
          setUserState({
            username: data.username ?? "User",
            email: data.email,
            first_name: data.first_name,
            last_name: data.last_name,
            id: data.id,
            role: data.role,
            can_access_admin: data.can_access_admin,
            is_admin: data.is_admin,
            avatar: data.avatar ?? null,
          });
        },
      )
      .catch(() => {
        auth.logout();
        setUserState(null);
      })
      .finally(() => setLoading(false));
  }, [setUserState]);

  return (
    <AuthContext.Provider value={{ user, setUser, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
