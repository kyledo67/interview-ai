import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Auth } from '../../Contexts/authcontext';
import { Login }from '../auth/login';
import { Register }from '../auth/register';
import styles from './Header.module.css';


const Header = () => {
    const [showloginmodal, setshowloginmodal] = useState(false);
    const [showregistermodal, setshowregistermodal] = useState(false);
    const { user, logout, isauthenticated } = Auth();
    const navigate = useNavigate();

    const handlegetstarted = () => {
        if (isauthenticated) {
            // Navigate to upload page
            navigate('/upload');
        } else {
            setshowregistermodal(true);
        }
    };

    const handlelogin = () => {
        if (isauthenticated) {
            // If already logged in, go to /upload
            navigate('/upload');
        } else {
            setshowloginmodal(true);
        }
    };

    const handlelogout = async () => {
        await logout();
    };

    const switchtoregister = () => {
        setshowloginmodal(false);
        setshowregistermodal(true);
    };

    const switchtologin = () => {
        setshowregistermodal(false);
        setshowloginmodal(true);
    };

    const closemodals = () => {
        setshowloginmodal(false);
        setshowregistermodal(false);
    };

    return (
        <>
            <header className={styles.header}>
                <div className={styles.headerContainer}>
                    <div
                        className={styles.logo}
                        onClick={() => navigate('/')}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && (navigate('/'))}
                    >
                        <img src="/logo.png" alt="logo" className={styles.logoimage} />
                    </div> 
                    
                    <div className={styles.navButtons}>
                        {isauthenticated ? (
                            // Logged in state - show start button and logout
                            <>
                                <span style={{
                                    color: 'rgba(255, 255, 255, 0.8)',
                                    fontSize: '14px',
                                    fontWeight: '500',
                                    marginRight: '8px'
                                }}>
                                </span>
                                <button 
                                    className={`${styles.ctaButton} ${styles.loginButton}`}
                                    onClick={() => navigate('/upload')}
                                >
                                    Start
                                </button>
                                <button 
                                    className={`${styles.ctaButton} ${styles.getStartedButton}`}
                                    onClick={handlelogout}
                                >
                                    Logout
                                </button>
                            </>
                        ) : (
                            // Not logged in state - show login and get started
                            <>
                                <button 
                                    className={`${styles.ctaButton} ${styles.loginButton}`}
                                    onClick={handlelogin}
                                >
                                    Log In
                                </button>
                                <button 
                                    className={`${styles.ctaButton} ${styles.getStartedButton}`}
                                    onClick={handlegetstarted}
                                >
                                    Get Started
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </header>

            {/* Modals */}
            <Login
                isopen={showloginmodal}
                onclose={closemodals}
                switchtoregister={switchtoregister}
            />
            <Register
                isopen={showregistermodal}
                onclose={closemodals}
                switchtologin={switchtologin}
            />
        </>
    );
};

export default Header;