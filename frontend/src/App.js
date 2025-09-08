import React from "react";
import "./App.css";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Authprovider } from "./Contexts/authcontext";
import Videosection from "./Components/Features/videosection";
import Landingpage from "./Pages/landingpage";
import Resumeupload from "./Pages/resumeupload";
import Interview from "./Pages/interview"

export default function App() {
  return (
    // authprovider wraps everything so all components can access auth state
    <Authprovider>
      <Router>
        <Routes>
          <Route path="/" element={<Landingpage />} />
          <Route path="/upload" element={<Resumeupload />} />
          <Route path="/interview" element={<Interview />} />
        </Routes>
      </Router>
    </Authprovider>
  );
}