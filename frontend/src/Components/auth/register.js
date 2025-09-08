import React, { useState } from 'react';
import { Auth } from '../../Contexts/authcontext';

const Register = ({ isopen, onclose, switchtologin }) => {
    const [email, setemail] = useState('');
    const [password, setpassword] = useState('');
    const [confirmpassword, setconfirmpassword] = useState('');
    const [message, setmessage] = useState('');
    const [isloading, setisloading] = useState(false);
    const { register } = Auth();

    // Handles registration form submission
    const handlesubmit = async (e) => {
        e.preventDefault();
        
        // Check if passwords match before sending to server
        if (password !== confirmpassword) {
            setmessage('Passwords do not match');
            return;
        }

        setisloading(true);
        setmessage('');

        const result = await register(email, password);
        
        if (result.success) {
            setmessage('Registration successful! Please login.');
            // Automatically switch to login modal after success
            setTimeout(() => {
                switchtologin();
            }, 2000);
        } else {
            setmessage(result.message);
        }
        setisloading(false);
    };

    if (!isopen) return null;

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1000
        }}>
            <div style={{
                backgroundColor: 'white',
                padding: '30px',
                borderRadius: '10px',
                width: '400px',
                maxWidth: '90vw'
            }}>
                <h2 style={{ marginBottom: '20px', textAlign: 'center', color: 'black' }}>Register</h2>
                
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
                    
                    <div style={{ marginBottom: '15px' }}>
                        <label style={{ display: 'block', marginBottom: '5px', color: 'black' }}>Password:</label>
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
                    
                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '5px', color: 'black' }}>Confirm Password:</label>
                        <input
                            type="password"
                            value={confirmpassword}
                            onChange={(e) => setconfirmpassword(e.target.value)}
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
                        {isloading ? 'Registering...' : 'Register'}
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
                    <p>Already have an account?{' '}
                        <button
                            onClick={switchtologin}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: '#007bff',
                                cursor: 'pointer',
                                textDecoration: 'underline'
                            }}
                        >
                            Login here
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

export { Register };