// Updated resumeupload.js
import React, { useState } from 'react';
import { Auth } from '../Contexts/authcontext';
import Protectedroute from '../Components/ProtectedRoute';

function Resumeupload() {
    const [selectedfile, setselectedfile] = useState(null);
    const [uploading, setuploading] = useState(false);
    const [msg, setmsg] = useState("");
    const { user } = Auth();

    const fileselect = (event) => {
        const file = event.target.files[0];
        if (file) {
            setselectedfile(file);
            setmsg("");
            console.log("File selected:", file.name, file.type, file.size);
        }
    };
    
    const uploadfile = async () => {
        if(!selectedfile) {
            setmsg("No file selected");
            return;
        }

        setuploading(true);
        setmsg("Uploading...");
        
        const formdata = new FormData();
        formdata.append("resume", selectedfile);
        //debug to see if it gets the right file
        console.log("file:", selectedfile.name);
        console.log("user:", user?.email);

        try {
            const response = await fetch("/resumeupload", {
                method: "POST",
                body: formdata,
                credentials: "include"
            });
            
            console.log("Response status:", response.status);
            console.log("Response ok:", response.ok);
            
            if (response.ok) {
                const result = await response.json();
                setmsg("Upload successful! Redirecting to interview...");
                console.log("nice");
                
                // Redirect to interview page after 2 seconds
                setTimeout(() => {
                    window.location.href = '/interview';
                }, 1000);
            } else {
                const error = await response.json();
                setmsg("Upload failed: " + error.detail);
                console.error("Upload failed:", error);
            }

        } catch(err) {
            console.error("Fetch error:", err);
            setmsg("Network error: " + err.message);
        }
        finally {
            setuploading(false);
        }
    };

    return (
        <Protectedroute>
            <div style={{
                display: "flex", 
                justifyContent: "center", 
                alignItems: "center", 
                height: "100vh", 
                flexDirection: "column",
                gap: "20px"
            }}>
                <h1>Resume Upload</h1>
                <p>Welcome, {user?.email}!</p>
                
                <input
                    id="resumeinput"
                    type="file"
                    accept=".pdf"
                    onChange={fileselect}
                    style={{display: "none"}}
                />

                <button
                    onClick={() => document.getElementById("resumeinput").click()}
                    style={{ 
                        padding: "15px 30px", 
                        fontSize: "16px",
                        backgroundColor: "#f4f4f4ff",
                        color: "black",
                        border: "none",
                        borderRadius: "8px",
                        cursor: "pointer"
                    }}
                >
                    Choose Resume File
                </button>

                {selectedfile && (
                <>
                    <div style={{
                        padding: "20px",
                        border: "2px dashed #ccc",
                        borderRadius: "8px",
                        textAlign: "center"
                    }}>
                        <p style={{ margin: "0", fontSize: "14px" }}>
                            Selected file: <strong>{selectedfile.name}</strong>
                        </p>
                        <p style={{ margin: "5px 0 0 0", fontSize: "12px", color: "#666" }}>
                            Size: {(selectedfile.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                    </div>
                    
                    <button 
                        onClick={uploadfile}
                        disabled={uploading}
                        style={{ 
                            padding: "15px 30px", 
                            fontSize: "16px",
                            backgroundColor: uploading ? "#6c757d" : "#28a745",
                            color: "white",
                            border: "none",
                            borderRadius: "8px",
                            cursor: uploading ? "not-allowed" : "pointer"
                        }}
                    > 
                        {uploading ? "Uploading..." : "Upload & Start Interview"} 
                    </button>
                </>
                )}

                {msg && (
                    <div style={{
                        padding: "15px",
                        borderRadius: "5px",
                        backgroundColor: msg.includes("successful") ? "#d4edda" : "#f8d7da",
                        color: msg.includes("successful") ? "#155724" : "#721c24",
                        border: `1px solid ${msg.includes("successful") ? "#c3e6cb" : "#f5c6cb"}`,
                        maxWidth: "500px",
                        textAlign: "center"
                    }}>
                        {msg}
                    </div>
                )}

                <button
                    onClick={() => window.location.href = '/'}
                    style={{
                        padding: "10px 20px",
                        backgroundColor: "#6c757d",
                        color: "white",
                        border: "none",
                        borderRadius: "5px",
                        cursor: "pointer",
                        marginTop: "20px"
                    }}
                >
                    Back to Home
                </button>
            </div>
        </Protectedroute>
    );
}

export default Resumeupload;