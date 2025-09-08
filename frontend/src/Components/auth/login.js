import React, { useState } from 'react';
import { Auth } from '../../Contexts/authcontext';

const Login = ({ isopen, onclose, switchtoregister }) => {
    const [email, setemail] = useState('');
    const [password, setpassword] = useState('');
    const [message, setmessage] = useState('');
    const [isloading, setisloading] = useState(false);
    const { login } = Auth();

    // Handles form submission when user clicks login button
    const handlesubmit = async (e) => {
        e.preventDefault(); // Prevents page refresh
        setisloading(true);
        setmessage('');

        const result = await login(email, password);
        
        if (result.success) {
            setmessage('Login successful!');
            // Close modal after short delay
            setTimeout(() => {
                onclose();
                setemail('');
                setpassword('');
                setmessage('');
            }, 500);
        } else {
            setmessage(result.message); // Show error message
        }
        setisloading(false);
    };

    // Don't render anything if modal should be closed
    if (!isopen) return null;

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)', // Semi-transparent overlay
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1000 // Ensures modal appears above everything
        }}>
            <div style={{
                backgroundColor: 'white',
                padding: '30px',
                borderRadius: '10px',
                width: '400px',
                maxWidth: '90vw'
            }}>
                <h2 style={{ marginBottom: '20px', textAlign: 'center', color: 'black' }}>Login</h2>
                
                <form onSubmit={handlesubmit}>
                    <div style={{ marginBottom: '15px' }}>
                        <label style={{ display: 'block', marginBottom: '5px', color: 'black' }}>Email:</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setemail(e.target.value)}
                            required
                            style={{
                                width: '100%',
                                padding: '10px',
                                border: '1px solid #ccc',
                                borderRadius: '5px',
                                boxSizing: 'border-box'
                            }}
                        />
                    </div>
                    
                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '5px', color: 'black'}}>Password:</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setpassword(e.target.value)}
                            required
                            style={{
                                width: '100%',
                                padding: '10px',
                                border: '1px solid #ccc',
                                borderRadius: '5px',
                                boxSizing: 'border-box'
                            }}
                        />
                    </div>
                    
                    <button
                        type="submit"
                        disabled={isloading}
                        style={{
                            width: '100%',
                            padding: '12px',
                            backgroundColor: '#007bff',
                            color: 'white',
                            border: 'none',
                            borderRadius: '5px',
                            cursor: isloading ? 'not-allowed' : 'pointer',
                            marginBottom: '15px'
                        }}
                    >
                        {isloading ? 'Logging in...' : 'Login'}
                    </button>
                </form>
                
                {message && (
                    <p style={{
                        textAlign: 'center',
                        color: message.includes('successful') ? 'green' : 'red',
                        marginBottom: '15px'
                    }}>
                        {message}
                    </p>
                )}
                
                <div style={{ textAlign: 'center', color: 'black' }}>
                    <p>Don't have an account?{' '}
                        <button
                            onClick={switchtoregister}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: '#007bff',
                                cursor: 'pointer',
                                textDecoration: 'underline'
                            }}
                        >
                            Register here
                        </button>
                    </p>
                    
                    <button
                        onClick={onclose}
                        style={{
                            marginTop: '10px',
                            padding: '8px 20px',
                            backgroundColor: '#6c757d',
                            color: 'white',
                            border: 'none',
                            borderRadius: '5px',
                            cursor: 'pointer'
                        }}
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
};

export { Login };