import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

const authcontext = createContext();


export const Auth = () => {
    const context = useContext(authcontext);
    if (!context) {
        throw new Error('no authprovider');
    }
    return context;
};

export const Authprovider = ({ children }) => {
    const [user, setuser] = useState(null);
    const [loading, setloading] = useState(true);
    const refreshIntervalRef = useRef(null);

   
    useEffect(() => {
        console.log('🔄 useEffect: Initial mount, calling checkauth');
        checkauth();
        
        // clean interval on unmount
        return () => {
            console.log('🧹 useEffect: Component unmounting, clearing interval');
            if (refreshIntervalRef.current) {
                clearInterval(refreshIntervalRef.current);
            }
        };
    }, []);

    // set up automatic token refresh when user is authenticated
    useEffect(() => {
        if (user) {
            console.log('   Setting up token refresh');
            setupTokenRefresh();
        } else {
            console.log('   Clearing token refresh');
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
        } else {
            console.log('No interva');
        }
    };

 
    const refreshToken = async () => {
        try {
            const response = await fetch('http://localhost:8001/refresh', {
                method: 'POST',
                credentials: 'include'
            });

            console.log('   Refresh response status:', response.status);
            if (response.ok) {
                return true;
            } else {
                await logout();
                return false;
            }
        } catch (error) {
            await logout();
            return false;
        }
    };

   
    const apiCall = async (url, options = {}) => {

        try {
            console.log('   Making initial fetch...');
            let response = await fetch(url, {
                ...options,
                credentials: 'include'
            });

            console.log('   Response status:', response.status);
    
            if (response.status === 401) {
                const refreshSuccess = await refreshToken();
                
                if (refreshSuccess) {
                    response = await fetch(url, {
                        ...options,
                        credentials: 'include'
                    });
                } else {
                    throw new Error('auth failed');
                }
            }

            return response;
        } catch (error) {
            console.error(error)
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
            
            setuser(null);
        } finally {
            
            setloading(false); 
        }
    };


    const login = async (email, password) => {
        
        
        try {
            console.log('   Fetching /login endpoint...');
            const response = await fetch('http://localhost:8001/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include', 
                body: JSON.stringify({ email, password }),
            });

            console.log('   Login response status:', response.status);
            console.log('   Login response ok:', response.ok);
            console.log('   Login response headers:', Object.fromEntries(response.headers.entries()));

            if (response.ok) {
                const data = await response.json();
             
                
               
                await checkauth();
                console.log('efnoiuehsfhnfn');
                return { success: true, message: data.message };
            } else {
                console.log('auth no work');
                const error = await response.json();
                console.error('   Error detail:', error);
                return { success: false, message: error.detail };
            }
        } catch (error) {
            console.error(error.name);
            console.error(error.message);
            console.error('Full error:', error);
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
                console.log('success');
                return { success: true, message: 'Registration successful' };
            } else {
                console.log('register failed');
                const error = await response.json();
                console.error('Error:', error);
                return { success: false, message: error.detail };
            }
        } catch (error) {
            console.error('Error name:', error.name);
            console.error('Error message:', error.message);
            console.error('Full error:', error);
            return { success: false, message: ' error' };
        }
    };

   
    const logout = async () => {
        clearTokenRefresh();
        
        console.log('   Clearing cookies...');
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