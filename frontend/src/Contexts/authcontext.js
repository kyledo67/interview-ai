import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

const authcontext = createContext();


export const Auth = () => {
    const context = useContext(authcontext);
    if (!context) {
        throw new Error('Auth must be used within authprovider');
    }
    return context;
};

export const Authprovider = ({ children }) => {
    const [user, setuser] = useState(null);
    const [loading, setloading] = useState(true);
    const refreshIntervalRef = useRef(null);

   
    useEffect(() => {
        checkauth();
        
        // Cleanup interval on unmount
        return () => {
            if (refreshIntervalRef.current) {
                clearInterval(refreshIntervalRef.current);
            }
        };
    }, []);

    // set up automatic token refresh when user is authenticated
    useEffect(() => {
        if (user) {
            setupTokenRefresh();
        } else {
            clearTokenRefresh();
        }
    }, [user]);

    const setupTokenRefresh = () => {
        clearTokenRefresh(); 
        
        refreshIntervalRef.current = setInterval(async () => {
            console.log('Auto-refreshing token...');
            await refreshToken();
        }, 25 * 60 * 1000); 
    };

   
    const clearTokenRefresh = () => {
        if (refreshIntervalRef.current) {
            clearInterval(refreshIntervalRef.current);
            refreshIntervalRef.current = null;
        }
    };

 
    const refreshToken = async () => {
        try {
            const response = await fetch('http://localhost:8001/refresh', {
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

   
    const apiCall = async (url, options = {}) => {
       
        console.log(url);
        try {
            let response = await fetch(url, {
                ...options,
                credentials: 'include'
            });

    
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
                   
                    throw new Error('Authentication failed');
                }
            }

            return response;
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    };

  
    const checkauth = async () => {
        try {
            const response = await apiCall('http://localhost:8001/me');
            if (response.ok) {
                const userdata = await response.json();
                setuser(userdata); 
            } else {
                setuser(null);
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            setuser(null);
        } finally {
            setloading(false); 
        }
    };


    const login = async (email, password) => {
        try {
            const response = await fetch('http://localhost:8001/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include', 
                body: JSON.stringify({ email, password }),
            });

            if (response.ok) {
                const data = await response.json();
                
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

    const register = async (email, password) => {
        try {
            const response = await fetch('http://localhost:8001/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
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

   
    const logout = async () => {
        clearTokenRefresh();
        
        // Clear cookies by making them expire immediately
        document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        document.cookie = "refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        setuser(null); 
    };

    // Values available to all components using Auth()
    const value = {
        user,
        login,
        register,
        logout,
        loading,
        isauthenticated: !!user, 
        apiCall, 
        refreshToken 
    };

    return (
        <authcontext.Provider value={value}>
            {children}
        </authcontext.Provider>
    );
};