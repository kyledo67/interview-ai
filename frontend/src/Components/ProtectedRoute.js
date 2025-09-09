import React from 'react';
import { Auth } from '../Contexts/authcontext';
import { useNavigate } from 'react-router-dom';

const Protectedroute = ({ children }) => {
    const { isauthenticated, loading } = Auth();
    const navigate = useNavigate();
    // Show loading spinna while checking authentication
    if (loading) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh'
            }}>
                <p>Loading...</p>
            </div>
        );
    }

    // If user is not logged in, show message and redirect option
    if (!isauthenticated) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
                flexDirection: 'column',
                gap: '20px'
            }}>
                <h2>Please log in to access this page</h2>
                <button
                    onClick={() => window.location.href = '/'}
                    style={{
                        padding: '10px 20px',
                        backgroundColor: '#007bff',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: 'pointer'
                    }}
                >
                    Go to Home
                </button>
            </div>
        );
    }

    // If user is authenticated, show the protected content
    return children;
};

export default Protectedroute;



