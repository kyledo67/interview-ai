import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

const authcontext = createContext();

// Custom hook to use auth anywhere
export const Auth = () => {
    const context = useContext(authcontext);
    if (!context) {
        throw new Error('Auth must be used within authprovider');
    }
    return context;
};

// Wrapper component that provides auth to all child components
export const Authprovider = ({ children }) => {
    const [user, setuser] = useState(null);
    const [loading, setloading] = useState(true);
    const refreshIntervalRef = useRef(null);

    // Check if user is already logged in when app starts
    useEffect(() => {
        checkauth();
        
        // Cleanup interval on unmount
        return () => {
            if (refreshIntervalRef.current) {
                clearInterval(refreshIntervalRef.current);
            }
        };
    }, []);

    // Set up automatic token refresh when user is authenticated
    useEffect(() => {
        if (user) {
            setupTokenRefresh();
        } else {
            clearTokenRefresh();
        }
    }, [user]);

    // Setup automatic token refresh every 25 minutes (before 30min expiry)
    const setupTokenRefresh = () => {
        clearTokenRefresh(); // Clear any existing interval
        
        refreshIntervalRef.current = setInterval(async () => {
            console.log('Auto-refreshing token...');
            await refreshToken();
        }, 25 * 60 * 1000); // 25 minutes
    };

    // Clear the refresh interval
    const clearTokenRefresh = () => {
        if (refreshIntervalRef.current) {
            clearInterval(refreshIntervalRef.current);
            refreshIntervalRef.current = null;
        }
    };

    // Refresh the access token using refresh token
    const refreshToken = async () => {
        try {
            const response = await fetch('/refresh', {
                method: 'POST',
                credentials: 'include'
            });

            if (response.ok) {
                console.log('Token refreshed successfully');
                return true;
            } else {
                console.log('Token refresh failed, logging out...');
                await logout();
                return false;
            }
        } catch (error) {
            console.error('Token refresh error:', error);
            await logout();
            return false;
        }
    };

    // api call function that handles token refresh automatically
    const apiCall = async (url, options = {}) => {
        // debug: making sure it's the right url
        console.log(url);
        try {
            let response = await fetch(url, {
                ...options,
                credentials: 'include'
            });

            // If  401, try to refresh token and retry
            if (response.status === 401) {
                console.log('Got 401, attempting token refresh...');
                const refreshSuccess = await refreshToken();
                
                if (refreshSuccess) {
                    // Retry the original request
                    response = await fetch(url, {
                        ...options,
                        credentials: 'include'
                    });
                } else {
                    // Refresh failed, user will be logged out by refreshToken function
                    throw new Error('Authentication failed');
                }
            }

            return response;
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    };

    // Calls backend to see if user has valid session cookies
    const checkauth = async () => {
        try {
            const response = await apiCall('/me');
            if (response.ok) {
                const userdata = await response.json();
                setuser(userdata); // Store user info in state
            } else {
                setuser(null);
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            setuser(null);
        } finally {
            setloading(false); // Stop loading spinner
        }
    };

    // Handles login form submission
    const login = async (email, password) => {
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include', // Important: allows cookies to be set
                body: JSON.stringify({ email, password }),
            });

            if (response.ok) {
                const data = await response.json();
                // Check current user after successful login
                await checkauth();
                return { success: true, message: data.message };
            } else {
                const error = await response.json();
                return { success: false, message: error.detail };
            }
        } catch (error) {
            return { success: false, message: 'error' };
        }
    };

    // Handles registration form submission
    const register = async (email, password) => {
        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password })
            });

            if (response.ok) {
                return { success: true, message: 'Registration successful' };
            } else {
                const error = await response.json();
                return { success: false, message: error.detail };
            }
        } catch (error) {
            return { success: false, message: ' error' };
        }
    };

    // Clears user session by removing cookies
    const logout = async () => {
        // Clear the refresh interval
        clearTokenRefresh();
        
        // Clear cookies by making them expire immediately
        document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        document.cookie = "refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        setuser(null); // Clear user from state
    };

    // Values available to all components using Auth()
    const value = {
        user,
        login,
        register,
        logout,
        loading,
        isauthenticated: !!user, // Converts user object to true/false
        apiCall, // Expose the enhanced API call function
        refreshToken // Expose manual refresh function if needed
    };

    return (
        <authcontext.Provider value={value}>
            {children}
        </authcontext.Provider>
    );
};