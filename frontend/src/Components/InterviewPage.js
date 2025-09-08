import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Camera, CameraOff, Phone, Send } from 'lucide-react';
import './InterviewPage.css';
import Editor from '@monaco-editor/react';


const MonacoEditor = ({ value, onChange, language = "javascript" }) => {
  return (
    <div className="monaco-editor-container">
      <Editor
        height="100%" 
        language={language}
        value={value}
        onChange={onChange}
        theme="vs-dark"
        options={{
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: 'on',
          roundedSelection: false,
          scrollBeyondLastLine: false,
          automaticLayout: true, 
          tabSize: 2,
          wordWrap: 'on'
        }}
      />
    </div>
    
  );
}
const InterviewPage = () => {
  const [currentPhase, setCurrentPhase] = useState('behavioral');
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isMicOn, setIsMicOn] = useState(true);
  const [isCameraOn, setIsCameraOn] = useState(true);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  // Stores the code that the user is writing in the technical phase
  const [code, setCode] = useState('');
  // Stores which programming language is selected
  const [selectedLanguage, setSelectedLanguage] = useState(71);
  // Stores the current coding problem being shown to the user
  const [currentProblem, setCurrentProblem] = useState(null);
  // Stores the output from running the user's code
  const [output, setOutput] = useState('');
  // Tracks whether code is currently being executed
  const [isExecuting, setIsExecuting] = useState(false);
  // Controls whether the end call confirmation dialog is visible
  const [showEndCallDialog, setShowEndCallDialog] = useState(false);
  const [interviewId, setInterviewId] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const userVideoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const speechRecognitionRef = useRef(null);
  const isMicOnRef = useRef(isMicOn); 
  const streamRef = useRef(null);

  const problems = [
    {
      id: 1, 
      title: "Two Sum", 
      description: "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
      examples: [
        { input: "[2,7,11,15], target = 9", output: "[0,1]" },
        { input: "[3,2,4], target = 6", output: "[1,2]" }
      ],
      testCases: [
        // Test cases for Judge0 API to validate the code
        { input: "[2,7,11,15]\n9", expected: "[0,1]" },
        { input: "[3,2,4]\n6", expected: "[1,2]" }
      ]
    }
    // More problems soon
  ];

  // Programming languages for Judge0 API
  const languages = [
    { id: 71, name: "Python", monaco: "python" }, 
    { id: 62, name: "Java", monaco: "java" },
    { id: 63, name: "JavaScript", monaco: "javascript" },
    { id: 54, name: "C++", monaco: "cpp" }
  ];

 
  useEffect(() => {
    initializeWebcam(); // Start the user's webcam
    selectRandomProblem(); // Pick a random coding problem for later
    startInterview(); // Start the interview with backend
    initializeSpeechRecognition(); // Initialize speech recognition
  }, []); 

  // Cleanup when component unmounts
  useEffect(() => {
    return () => {
      if (speechRecognitionRef.current) {
        speechRecognitionRef.current.stop();
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);
  //just to set the editor w the pre coding things languages might need
  useEffect(() => {
    const currentLang = languages.find(l => l.id === selectedLanguage);
    
    if (currentLang?.monaco === 'java') {
        setCode(`public class InterviewAi {
        public static void main(String[] args) {
            
            
        }
    }`);
    } else if(currentLang?.monaco == "cpp") {
      setCode(`#include <iostream> \n#include <string>\n\nusing namespace std;\nint main() {\n\t return 0;\n}`
      )
    }
    else if (currentLang?.monaco !== 'java' || currentLang?.monaco !== 'cpp') {
        setCode(''); 
    }
}, [selectedLanguage]);


  useEffect(() => {
    isMicOnRef.current = isMicOn;
    //set speaking to false when mic is turned off
    if (!isMicOn) {
      setIsUserSpeaking(false);
    }
  }, [isMicOn]);

  // Update video stream when phase changes or video ref changes
  useEffect(() => {
    if (streamRef.current && userVideoRef.current) {
      userVideoRef.current.srcObject = streamRef.current;
    }
  }, [currentPhase]); // Re-run when phase changes


  // Function to access camera and microphone
  const initializeWebcam = async () => {
    try {
      // Request access to camera and microphone
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: true  
      });
      
      // Store the stream for reuse
      streamRef.current = stream;
      
     
      if (userVideoRef.current) {
        // Connect the camera stream to the video element
        userVideoRef.current.srcObject = stream;
      }

      //speech detection
      initializeAudioAnalysis(stream);
      
    } catch (error) {
      // If user denies permission or camera not available
      console.error('Error getting webcam:', error);
    }
  };


  const initializeAudioAnalysis = (stream) => {
    try {
      // Create audio context for getting microphone input
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      const audioContext = audioContextRef.current;
      
      // Create audio source from microphone stream
      const source = audioContext.createMediaStreamSource(stream);
      
      // Create analyser to measure audio levels
      analyserRef.current = audioContext.createAnalyser();
      analyserRef.current.fftSize = 256;
      
      // Connect source to analyser
      source.connect(analyserRef.current);
      
      // Start monitoring audio levels
      monitorAudioLevels();
      
    } catch (error) {
      console.error('Error getting audio lvls:', error);
    }
  };

  // Monitor audio levels to detect speech
  const monitorAudioLevels = () => {
    if (!analyserRef.current) return;
    
    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const checkAudioLevel = () => {
      // Only analyze audio if mic is on
      if (isMicOnRef.current && analyserRef.current) {
        analyserRef.current.getByteFrequencyData(dataArray);
        
        // Calculate average volume level
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const average = sum / bufferLength;
        
        // Threshold for detecting speech
        const speechThreshold = 20;
        
        // Update speaking state based on volume level
        setIsUserSpeaking(average > speechThreshold);
      } else {
        // If mic is off, user != speaking
        setIsUserSpeaking(false);
      }
      
      // Continue monitoring
      requestAnimationFrame(checkAudioLevel);
    };
    
    checkAudioLevel();
  };


const initializeSpeechRecognition = () => {
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
    speechRecognitionRef.current = new SpeechRecognition();
    
    const recognition = speechRecognitionRef.current;
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;
    
    recognition.onstart = () => {
      console.log('Speech started');
      setIsRecording(true);
    };
    
    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          const transcript = event.results[i][0].transcript.trim();
          if (transcript) {
            addToTranscript('user', transcript);
          }
        }
      }
    };
    
    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      
      // Don't stop completely on no speech or audio log error, js log them
      if (event.error === 'no-speech' || event.error === 'audio-capture') {
        console.log('retrying speech recognition...');
        return;
      }
      
      // For other errors, stop recording
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        console.error('permission not allowed for speech recognition');
        setIsRecording(false);
        return;
      }
    };
    
    recognition.onend = () => {
      console.log('Speech ended');
      
      // Only restart if mic is still on
      if (isMicOnRef.current) {
        console.log('restarting');
        setTimeout(() => {
          try {
            if (speechRecognitionRef.current && isMicOnRef.current) {
              speechRecognitionRef.current.start();
            }
          } catch (error) {
            console.error('cant restart speech recognition:', error);
            // Wait b4 trying again
            setTimeout(() => {
              if (speechRecognitionRef.current && isMicOnRef.current) {
                try {
                  speechRecognitionRef.current.start();
                } catch (retryError) {
                  console.error('retry failed:', retryError);
                  setIsRecording(false);
                }
              }
            }, 2000);
          }
        }, 100);
      } else {
        setIsRecording(false);
      }
    };
    
    // Start recognition if mic is on
    if (isMicOn) {
      try {
        recognition.start();
        setIsRecording(true);
      } catch (error) {
        console.error('error', error);
        setIsRecording(false);
      }
    }
  } else {
    console.warn('Speech recognition isnt supported here');
  }
};


const ToggleMicrophone = () => {
  const newMicState = !isMicOn;
  setIsMicOn(newMicState);
  
  if (newMicState) {
    
    // goodbye old instance and create new one
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.abort();
      } catch (error) {
        console.log('erorr', error);
      }
      speechRecognitionRef.current = null;
    }
    
    setIsRecording(false);
    
    // Wait then create completely fresh instance
    setTimeout(() => {
      if (isMicOn) { // Check current state
        console.log('new instance');
        initializeSpeechRecognition();
      }
    }, 300);
    
  } else {
    
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.abort();
      } catch (error) {
        console.error('Error', error);
      }
    }
    
    setIsRecording(false);
    setIsUserSpeaking(false);
  }
};

// Add message to transcript
const addToTranscript = (speaker, message) => {
  const newMessage = {
    timestamp: new Date(),
    speaker: speaker,
    message: message
  };
  
  setTranscript(prev => [...prev, newMessage]);
  
  console.log('transcript:', newMessage);
  
  // TODO: Send to AI in real-time for live conversation
  if (speaker === 'user') {
    // This is where you'd send user messages to AI immediately
    // sendToAI(message);
  }
};

  
  // Start interview with backend
  const startInterview = async () => {
    try {
      // cookie-based auth
      const response = await fetch('http://localhost:8001/interviews/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        setInterviewId(result.interviewid);
        console.log('Interview started, id:', result.interviewid);
      } else {
        const errorData = await response.text();
        console.error('couldnt start:', response.status, response.statusText);
        console.error('boi error:', errorData);
        
        if (response.status === 401) {
            console.error('error')
            window.location.href = '/'
        } 
      }
    } catch (error) {
      console.error('Error starting interview:', error);
    }
  };

  // End interview with backend
  const endInterviewWithBackend = async () => {
    if (!interviewId) {
      console.log('No interview ID - skipping backend end call');
      return;
    }
    
    try {
      const response = await fetch(`http://localhost:8001/interviews/${interviewId}/end`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', 
        body: JSON.stringify({
          transcript: transcript.map(msg => ({
            timestamp: msg.timestamp,
            speaker: msg.speaker,
            message: msg.message
          }))
        })
      });
      
      if (response.ok) {
        console.log('Interview ended successfully');
        console.log('Final transcript sent:', transcript);
      } else {
        const errorData = await response.text();
        console.error('Failed to end interview:', response.status, response.statusText);
        console.error('Error details:', errorData);
      }
    } catch (error) {
      console.error('Error ending interview:', error);
    }
  };

  
  // Function to randomly pick a coding problem for the technical phase
  const selectRandomProblem = () => {
    // Check if problems available
    if (problems.length > 0) {
      // Generate a random number between 0 and the number of problems
      const randomIndex = Math.floor(Math.random() * problems.length);
      // Set the randomly selected problem as the current one
      setCurrentProblem(problems[randomIndex]);
    }
  };


  // Function that the AI will call when it wants to switch to technical phase
  const transitionToTechnical = () => {
    // Start the transition animation
    setIsTransitioning(true);
    
    // After 0.8 sec, complete the transition
    setTimeout(() => {
      setCurrentPhase('technical'); // Switch to technical phase
      setIsTransitioning(false);    // End the animation
    }, 800); 
  };

  
  // Function to send user's code to Judge0 API for execution
  const executeCode = async () => {
    // Don't execute if there's no code written
    if (!code.trim()) return;
    
    // Show loading state to user
    setIsExecuting(true);
    
    try {
      // Send POST request to backend API endpoint
      const response = await fetch('http://localhost:8001/code/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json', 
        },
        body: JSON.stringify({
          source_code: code,                              // The user's code
          language_id: selectedLanguage,                  // Programming language ID
          stdin: currentProblem?.testCases[0]?.input || "" // Test input data
        })
      });
      
      // Convert response to JSON
      const result = await response.json();
      
      // Handle different types of output from Judge0
      if (result.stdout) {
        // Code ran successfully and produced output
        setOutput(`Output:\n${result.stdout}`);
      } else if (result.stderr) {
        // Code had runtime errors
        setOutput(`Error:\n${result.stderr}`);
      } else if (result.compile_output) {
        // Code had compilation errors
        setOutput(`Compilation Error:\n${result.compile_output}`);
      } else {
        // No output received
        setOutput('No output received');
      }
    } catch (error) {
      //Network error or API unavailable cus free one :(
      setOutput(`Execution failed: ${error.message}`);
    } finally {
      //Always hide loading state when done
      setIsExecuting(false);
    }
  };

  
  //Function called when user ends interview
  const handleEndCall = () => {
    //confirmation dialog 
    setShowEndCallDialog(true);
  };

  //Function called when user confirms they want to end the interview
  const confirmEndCall = async () => {
    // Stop speech recognition
    if (speechRecognitionRef.current) {
      speechRecognitionRef.current.stop();
    }
    
    // End interview with backend
    await endInterviewWithBackend();
    
    console.log('Interview ended');
    setShowEndCallDialog(false);
    
    window.location.href = '/'; // Change to your desired landing page URL
  };

  // Function called when user decides not to end the interview
  const cancelEndCall = () => {
    // Just hide the dialog and continue the interview
    setShowEndCallDialog(false);
  };

  //mic toggle
  const toggleMicrophone = () => {
    const newMicState = !isMicOn;
    setIsMicOn(newMicState);
    
    if (speechRecognitionRef.current) {
      if (newMicState) {
        // Start speech recognition when mic is turned on
        speechRecognitionRef.current.start();
        setIsRecording(true);
      } else {
        // Stop speech recognition when mic is turned off
        speechRecognitionRef.current.stop();
        setIsRecording(false);
        setIsUserSpeaking(false); // Stop showing speaking indicator
      }
    }
  };

  return (
    // Main container 
    <div className="interview-container">
      {/* header */}
      <div className="header-bar">
        {/* Left side - App title */}
        <div className="header-title">
          <h2>InterviewAI</h2>
        </div>

        {/* Right side - Control buttons */}
        <div className="header-controls">
          {/* Microphone toggle button */}
          <button
            onClick={toggleMicrophone} // Use new toggle function
            className={`control-button ${isMicOn ? 'mic-on' : 'mic-off'}`}
          >
            {/* Show different icon based on mic state */}
            {isMicOn ? <Mic size={20} /> : <MicOff size={20} />}
          </button>
          
          {/* Camera toggle button */}
          <button
            onClick={() => setIsCameraOn(!isCameraOn)} // Toggle camera state when clicked
            className={`control-button ${isCameraOn ? 'camera-on' : 'camera-off'}`}
          >
            {/* Show different icon based on camera state */}
            {isCameraOn ? <Camera size={20} /> : <CameraOff size={20} />}
          </button>

          {/* End call button */}
          <button 
            onClick={handleEndCall} // Show confirmation dialog when clicked
            className="control-button end-call"
          >
            <Phone size={20} />
          </button>
        </div>
      </div>

      {/*middle/main*/}
      <div className="main-content">
    
        {/* if currentPhase === 'behavioral' */}
        {currentPhase === 'behavioral' && (
          <div className={`behavioral-phase ${isTransitioning ? 'transitioning' : ''}`}>
            {/* Container centering the two video boxes */}
            <div className="video-container-behavioral">
              
              {/* User's video box */}
              <div className={`video-box-large ${isUserSpeaking ? 'speaking' : ''}`}>
                {/* video element showing user's webcam */}
                <video
                  ref={userVideoRef}        // Reference to control this element
                  autoPlay                  // Start playing immediately
                  muted                    
                  className="video-element" 
                />
                
                {/* name */}
                <div className="video-label">
                  <span>You</span>
                </div>
                
                {/* Show camera off icon when camera is disabled */}
                {!isCameraOn && (
                  <div className="camera-off-overlay">
                    <CameraOff size={48} />
                  </div>
                )}
              </div>

              {/* AI's */}
              <div className={`video-box-large ${isAISpeaking ? 'speaking' : ''}`}>
                <div className="aivideo-element">
                  <img src="/aipfp.png" alt="aipfp"/>
                </div>
                
                
                {/* Label showing this is the AI */}
                <div className="video-label">
                  <span>Interviewer</span>
                </div>
              </div>
            </div>

            {/* Button to manually test phase transition */}
            <div className="test-button-container">
              <button
                onClick={transitionToTechnical}
                className="test-button"
              >
                Technical
              </button>
            </div>
          </div>
        )}

        {/* if currentPhase === 'technical' */}
        {currentPhase === 'technical' && (
          <div className={`technical-phase ${isTransitioning ? 'transitioning' : ''}`}>
            
            {/*left side video panels*/}
            <div className="video-sidebar">
              
              {/* User video */}
              <div className={`video-box-small ${isUserSpeaking ? 'speaking' : ''}`}>
                <video
                  ref={userVideoRef}
                  autoPlay
                  muted
                  className="video-element"
                />
                <div className="video-label-small">
                  You
                </div>
                {/* Camera off overlay */}
                {!isCameraOn && (
                  <div className="camera-off-overlay">
                    <CameraOff size={24} />
                  </div>
                )}
              </div>

              {/* AI pic */}
              <div className={`video-box-small ${isAISpeaking ? 'speaking' : ''}`}>
                <div className="aivideo-element">
                  <img src="/aipfp.png" alt="aipfp"/>
                </div>
                <div className="video-label-small">
                  Interviewer
                </div>
              </div>
            </div>

            {/* right side, coding interface*/}
            <div className="coding-interface">
              <div className="coding-container">
            
                {/* Top section showing the coding problem details */}
                <div className="problem-description">
                  {currentProblem ? (
                    <div>
                      {/* Problem title */}
                      <div className="problem-header">
                        <h3 className="problem-title">{currentProblem.title}</h3>
                      </div>
                      
                      {/* Problem description */}
                      <p className="problem-text">{currentProblem.description}</p>
                      
                      {/* Example inputs and outputs */}
                      <div className="examples-section">
                        <h4 className="examples-title">Examples:</h4>
                        {currentProblem.examples.map((example, index) => (
                          <div key={index} className="example-item">
                            <div className="example-input">Input: {example.input}</div>
                            <div className="example-output">Output: {example.output}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    // Show loading message if no problem is selected yet
                    <div className="loading-text">Loading problem...</div>
                  )}
                </div>

                {/* code editor*/}
                <div className="editor-section">
                  
                  {/* control bar with language selector and run button */}
                  <div className="editor-controls">
                    {/* programming language dropdown */}
                    <select
                      value={selectedLanguage}                    // Current selected language
                      onChange={(e) => setSelectedLanguage(parseInt(e.target.value))} // Update when changed
                      className="language-select"
                    >
                      {/* Create dropdown options from the languages array */}
                      {languages.map((lang) => (
                        <option key={lang.id} value={lang.id}>
                          {lang.name}
                        </option>
                      ))}
                    </select>

                    {/* Run code button */}
                    <button
                      onClick={executeCode}                       // Execute code when clicked
                      disabled={isExecuting}                     // Disable during execution
                      className="run-button"
                    >
                      <Send size={16} />
                      {/* Show different text based on execution state */}
                      <span>{isExecuting ? 'Running...' : 'Run Code'}</span>
                    </button>
                  </div>

                  {/* output panel and editor*/}
                  <div className="editor-output-container">
                    
                    {/* Code editor panel - where user writes code */}
                    <div className="editor-panel">
                      <MonacoEditor
                        value={code}                             // Current code content
                        onChange={setCode}                       // Update code when user types
                        language={languages.find(l => l.id === selectedLanguage)?.monaco || 'javascript'} // Set syntax highlighting
                      />
                    </div>

                    {/* Output panel - shows execution results */}
                    <div className="output-panel">
                      <h4 className="output-title">Output:</h4>
                      {/* Pre-formatted text to preserve spacing and line breaks */}
                      <pre className="output-content">
                        {output || 'Run your code to see output...'}
                      </pre>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* endcall dialog */}
      {/* pop up dialog that appears when user tries to end the interview */}
      {showEndCallDialog && (
        // Full screen overlay with semi-transparent background
        <div className="dialog-overlay">
          {/* The actual dialog box */}
          <div className="dialog-content">
            {/* Dialog title */}
            <h3 className="dialog-title">End Interview?</h3>
            
            {/* Warning message */}
            <p className="dialog-text">
              Are you sure you want to cancel the interview? This action cannot be undone.
            </p>
            
            {/* Action buttons */}
            <div className="dialog-buttons">
              {/* Confirm end interview button */}
              <button
                onClick={confirmEndCall}
                className="dialog-button confirm"
              >
                Yes, End Interview
              </button>
              
              {/* Cancel and continue interview button */}
              <button
                onClick={cancelEndCall}
                className="dialog-button cancel"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InterviewPage;