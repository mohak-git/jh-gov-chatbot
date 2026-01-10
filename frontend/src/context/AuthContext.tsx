"use client";

import { useRouter } from "next/navigation";
import {
    createContext,
    ReactNode,
    useContext,
    useEffect,
    useState,
} from "react";

interface User {
    username: string;
    email: string;
    role: string;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (
        token: string,
        username: string,
        email: string,
        role: string
    ) => void;
    logout: () => void;
    loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const API_URL = process.env.NEXT_PUBLIC_API_URL;

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const checkAuth = async () => {
            const storedToken = await localStorage.getItem("jhgovtchatbot_token");
            if (!storedToken) {
                setLoading(false);
                return;
            }

            try {
                const res = await fetch(`${API_URL}/auth/verify`, {
                    headers: { Authorization: `Bearer ${storedToken}` },
                });

                if (res.ok) {
                    const userData = await res.json();
                    setToken(storedToken);
                    setUser(userData);
                } else {
                    localStorage.removeItem("jhgovtchatbot_token");
                    localStorage.removeItem("jhgovtchatbot_user");
                    setToken(null);
                    setUser(null);
                }
            } catch (error) {
                console.error("Auth verification failed", error);
                localStorage.removeItem("jhgovtchatbot_token");
                localStorage.removeItem("jhgovtchatbot_user");
                setToken(null);
                setUser(null);
            } finally {
                setLoading(false);
            }
        };

        checkAuth();
    }, []);

    const login = (
        newToken: string,
        username: string,
        email: string,
        role: string
    ) => {
        const userData = { username, email, role };
        setToken(newToken);
        setUser(userData);
        localStorage.setItem("jhgovtchatbot_token", newToken);
        localStorage.setItem("jhgovtchatbot_user", JSON.stringify(userData));
        router.push("/");
    };

    const logout = () => {
        setToken(null);
        setUser(null);
        localStorage.removeItem("jhgovtchatbot_token");
        localStorage.removeItem("jhgovtchatbot_user");
        router.push("/login");
    };

    return (
        <AuthContext.Provider value={{ user, token, login, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined)
        throw new Error("useAuth must be used within an AuthProvider");

    return context;
};
