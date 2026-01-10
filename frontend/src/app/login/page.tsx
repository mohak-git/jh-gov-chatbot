"use client";

import { useAuth } from "@/context/AuthContext";
import Link from "next/link";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export default function LoginPage() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const { login } = useAuth();
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);

        try {
            const res = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: new URLSearchParams({ username, password }),
            });

            if (!res.ok) throw new Error("Invalid credentials");

            const data = await res.json();
            login(data.access_token, data.username, data.email, data.role);
        } catch (err) {
            setError("Login failed. Please check your credentials.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-900 p-4">
            <div className="w-full max-w-md space-y-8 rounded-lg bg-gray-800 p-6 shadow-xl">
                <h2 className="text-center text-3xl font-bold text-white">
                    Sign in
                </h2>
                {error && (
                    <div className="text-red-500 text-center">{error}</div>
                )}
                <form onSubmit={handleSubmit} className="mt-8 space-y-6">
                    <input
                        type="text"
                        required
                        className="w-full rounded bg-gray-700 p-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="Username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                    />
                    <input
                        type="password"
                        required
                        className="w-full rounded bg-gray-700 p-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full rounded bg-indigo-600 p-3 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
                        {isLoading ? "Signing in..." : "Sign in"}
                    </button>
                </form>
                <p className="text-center text-gray-400">
                    Don't have an account?{" "}
                    <Link
                        href="/register"
                        className="text-indigo-400 hover:text-indigo-300">
                        Sign up
                    </Link>
                </p>
            </div>
        </div>
    );
}
