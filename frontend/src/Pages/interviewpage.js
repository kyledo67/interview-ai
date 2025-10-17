import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Camera, CameraOff, Phone, Send } from 'lucide-react';
import './interviewpage.css';
import Editor from '@monaco-editor/react';
import { useNavigate } from 'react-router-dom';

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
  const navigate = useNavigate();
  
  const [code, setCode] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState(71);
  const [currentProblem, setCurrentProblem] = useState(null);
  const [output, setOutput] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [showEndCallDialog, setShowEndCallDialog] = useState(false);
  const [interviewId, setInterviewId] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isAIThinking, setIsAIThinking] = useState(false);
  const [candidateLevel, setCandidateLevel] = useState('');
  const [currentAIMessage, setCurrentAIMessage] = useState('');
  
  const userVideoRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const speechRecognitionRef = useRef(null);
  const isMicOnRef = useRef(isMicOn);
  const isAISpeakingRef = useRef(isAISpeaking);
  const streamRef = useRef(null);
  const speechSynthesisRef = useRef(null);
  const lastTranscriptLengthRef = useRef(0);
  const isInterviewStartingRef = useRef(false);
  const speechDebounceTimerRef = useRef(null);
  const pendingSpeechRef = useRef('');
  const languages = [
    { id: 71, name: "Python", monaco: "python" }, 
    { id: 62, name: "Java", monaco: "java" },
    { id: 63, name: "JavaScript", monaco: "javascript" },
    { id: 54, name: "C++", monaco: "cpp" }
  ];

  useEffect(() => {
    initializeWebcam();
    startInterview();
    initializeSpeechRecognition();
  }, []); 

  useEffect(() => {
  return () => {
      if (speechRecognitionRef.current) {
        speechRecognitionRef.current.stop();
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      if (speechSynthesisRef.current) {
        window.speechSynthesis.cancel();
      }
      if (speechDebounceTimerRef.current) {
        clearTimeout(speechDebounceTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const currentLang = languages.find(l => l.id === selectedLanguage);
    
    if (currentLang?.monaco === 'java') {
      setCode(`public class InterviewAi {
    public static void main(String[] args) {
        
    }
}`);
    } else if(currentLang?.monaco === "cpp") {
      setCode(`#include <iostream> 
#include <string>

using namespace std;
int main() {
    return 0;
}`);
    } else if (currentProblem?.starter_code) {
      setCode(currentProblem.starter_code);
    } else {
      setCode('');
    }
  }, [selectedLanguage, currentProblem]);

  useEffect(() => {
    isMicOnRef.current = isMicOn;
    if (!isMicOn) {
      setIsUserSpeaking(false);
    }
  }, [isMicOn]);

  useEffect(() => {
    isAISpeakingRef.current = isAISpeaking;
  }, [isAISpeaking]);

  useEffect(() => {
    if (streamRef.current && userVideoRef.current) {
      userVideoRef.current.srcObject = streamRef.current;
    }
  }, [currentPhase]);

  useEffect(() => {
    const handleNewUserMessage = async () => {
      if (transcript.length > lastTranscriptLengthRef.current) {
        const newMessages = transcript.slice(lastTranscriptLengthRef.current);
        const lastMessage = newMessages[newMessages.length - 1];
        
        if (lastMessage && lastMessage.speaker === 'User' && !isAISpeaking) {
          await sendMessageToAI(lastMessage.message);
        }
        
        lastTranscriptLengthRef.current = transcript.length;
      }
    };
    
    handleNewUserMessage();
  }, [transcript, isAISpeaking]);

  const initializeWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: true  
      });
      
      streamRef.current = stream;
      
      if (userVideoRef.current) {
        userVideoRef.current.srcObject = stream;
      }

      initializeAudioAnalysis(stream);
      
    } catch (error) {
      console.error('Error getting webcam:', error);
    }
  };

  const initializeAudioAnalysis = (stream) => {
    try {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      const audioContext = audioContextRef.current;
      
      const source = audioContext.createMediaStreamSource(stream);
      
      analyserRef.current = audioContext.createAnalyser();
      analyserRef.current.fftSize = 256;
      
      source.connect(analyserRef.current);
      
      monitorAudioLevels();
      
    } catch (error) {
      console.error('Error getting audio lvls:', error);
    }
  };

  const monitorAudioLevels = () => {
    if (!analyserRef.current) return;
    
    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const checkAudioLevel = () => {
      if (isMicOnRef.current && analyserRef.current && !isAISpeakingRef.current) {
        analyserRef.current.getByteFrequencyData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const average = sum / bufferLength;
        
        const speechThreshold = 20;
        
        setIsUserSpeaking(average > speechThreshold);
      } else {
        setIsUserSpeaking(false);
      }
      
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
      recognition.interimResults = true;
      recognition.lang = 'en-US';
      recognition.maxAlternatives = 1;
      
      recognition.onstart = () => {
        console.log('Speech started');
        setIsRecording(true);
      };
      
      recognition.onresult = (event) => {
        if (isAISpeakingRef.current) {
          console.log('AI is speaking, ignoring speech input');
          return;
        }
        
        // Clear existing debounce timer
        if (speechDebounceTimerRef.current) {
          clearTimeout(speechDebounceTimerRef.current);
        }
        
        let finalTranscript = '';
        let interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }
        
        // Store the current transcript (final + interim)
        const currentText = (finalTranscript + interimTranscript).trim();
        
        if (currentText) {
          pendingSpeechRef.current = currentText;
          
          // Wait 2 seconds of silence before sending to transcript
          speechDebounceTimerRef.current = setTimeout(() => {
            if (pendingSpeechRef.current && !isAISpeakingRef.current) {
              addToTranscript('User', pendingSpeechRef.current);
              pendingSpeechRef.current = '';
            }
          }, 1500); 
        }
      };
      
      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        
        if (event.error === 'no-speech' || event.error === 'audio-capture') {
          console.log('retrying speech recognition...');
          return;
        }
        
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          console.error('permission not allowed for speech recognition');
          setIsRecording(false);
          return;
        }
      };
      
      recognition.onend = () => {
        console.log('Speech ended');
        if (pendingSpeechRef.current && !isAISpeakingRef.current) {
          if (speechDebounceTimerRef.current) {
            clearTimeout(speechDebounceTimerRef.current);
          }
          addToTranscript('User', pendingSpeechRef.current);
          pendingSpeechRef.current = '';
        }
 
        if (isMicOnRef.current) {
          console.log('restarting');
          setTimeout(() => {
            try {
              if (speechRecognitionRef.current && isMicOnRef.current) {
                speechRecognitionRef.current.start();
              }
            } catch (error) {
              console.error('cant restart speech recognition:', error);
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
      
      if (isMicOnRef.current) {
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

  const toggleMicrophone = () => {
    const newMicState = !isMicOn;
    setIsMicOn(newMicState);
    isMicOnRef.current = newMicState;

    if (speechDebounceTimerRef.current) {
      clearTimeout(speechDebounceTimerRef.current);
    }
    pendingSpeechRef.current = '';

    if (newMicState) {
      
      if (speechRecognitionRef.current) {
        try {
          speechRecognitionRef.current.abort();
        } catch (error) {
          console.log('error', error);
        }
        speechRecognitionRef.current = null;
      }
      
      setIsRecording(false);
      
      setTimeout(() => {
        
        if (newMicState) {
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

  const addToTranscript = (speaker, message) => {
    const newMessage = {
      speaker: speaker,
      message: message,
      timestamp: new Date()
    };
    
    setTranscript(prev => [...prev, newMessage]);
    
    console.log('transcript:', newMessage);
  };

  const sendMessageToAI = async (userMessage) => {
    if (!interviewId) return;
    
    setIsAIThinking(true);
    
    try {
      const response = await fetch(`https://interview-ai-crdv.onrender.com/interviews/${interviewId}/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          message: userMessage,
          current_code: currentPhase === 'technical' ? code : null
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        addToTranscript('AI', data.ai_response);
        setCurrentAIMessage(data.ai_response);
        
        speakText(data.ai_response);
        
        if (data.should_switch_mode && data.new_mode === 'technical') {
          setTimeout(() => {
            transitionToTechnical(data.technical_data);
          }, 2000); 
        }
        else if (data.should_switch_mode && data.new_mode === 'candidate_questions') {
          setCurrentPhase('candidate_questions');
        }
        
        if (data.should_end_interview) {
          setTimeout(() => {
            confirmEndCall();
          }, 3000); 
        }
        
      } else {
        console.error('Failed to get AI response');
      }
    } catch (error) {
      console.error('Error sending message to AI:', error);
    } finally {
      setIsAIThinking(false);
    }
  };

  const speakText = async (text) => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    
    if (speechSynthesisRef.current) {
      speechSynthesisRef.current.pause();
      speechSynthesisRef.current = null;
    }
    
    setIsAISpeaking(true);
    
    try {
      const response = await fetch('https://interview-ai-crdv.onrender.com/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          text: text,
          voiceId: '19dbcb0f-e8c6-43de-a0a5-c210df202d2e'
        })
      });
      
      if (!response.ok) {
        throw new Error('tts failed');
      }
      
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      
      const audio = new Audio(audioUrl);
      speechSynthesisRef.current = audio;
      
      audio.onended = () => {
        setIsAISpeaking(false);
        URL.revokeObjectURL(audioUrl);
        speechSynthesisRef.current = null;
      };
      
      audio.onerror = () => {
        setIsAISpeaking(false);
        URL.revokeObjectURL(audioUrl);
        speechSynthesisRef.current = null;
      };
      
      await audio.play();
      
    } catch (error) {
      console.error('Error with ai speech:', error);
      setIsAISpeaking(false);
    }
  };

  const startInterview = async () => {
    if (isInterviewStartingRef.current) {
      console.log('Interview already starting, skipping duplicate call');
      return;
    }
    
    isInterviewStartingRef.current = true;
    
    try {
      const response = await fetch('https://interview-ai-crdv.onrender.com/interviews/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({})
      });
      
      if (response.ok) {
        const result = await response.json();
        setInterviewId(result.interview_id);
        setCandidateLevel(result.candidate_level);
        
        setCurrentAIMessage(result.ai_message);
        
        speakText(result.ai_message);
        
        console.log('Interview started, id:', result.interview_id);
      } else {
        const errorData = await response.text();
        console.error('couldnt start:', response.status, response.statusText);
        console.error('error:', errorData);
        
        if (response.status === 401) {
          console.error('unauthorized');
          window.location.href = '/';
        }
        isInterviewStartingRef.current = false;
      }
    } catch (error) {
      console.error('Error starting interview:', error);
      isInterviewStartingRef.current = false;
    }
  };

  const endInterviewWithBackend = async () => {
    if (!interviewId) {
      console.log('No interview ID - skipping backend end call');
      return;
    }
    
    try {
      const response = await fetch(`https://interview-ai-crdv.onrender.com/interviews/${interviewId}/end`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          transcript: transcript.map(msg => ({
            speaker: msg.speaker,
            message: msg.message,
            timestamp: msg.timestamp.toISOString()
          })),
          final_code: code
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Interview ended successfully');
        console.log('Evaluation:', data.evaluation);
        localStorage.setItem('lastInterviewEvaluation', JSON.stringify(data.evaluation));
      } else {
        const errorData = await response.text();
        console.error('Failed to end interview:', response.status, response.statusText);
        console.error('Error details:', errorData);
      }
    } catch (error) {
      console.error('Error ending interview:', error);
    }
  };

  const parseProblemDescription = (description) => {
    if (!description) return { main: '', examples: [], constraints: [] };
    
    const parts = description.split(/\*\*(Example \d+:|Constraints:|Follow-up:)\*\*/);
    
    const result = {
      main: parts[0].trim(),
      examples: [],
      constraints: '',
      followUp: ''
    };
    
    for (let i = 1; i < parts.length; i += 2) {
      const header = parts[i];
      const content = parts[i + 1]?.trim() || '';
      
      if (header.startsWith('Example')) {
        const lines = content.split('\n').filter(line => line.trim());
        const exampleObj = {};
        
        lines.forEach(line => {
          if (line.includes('Input:')) {
            exampleObj.input = line.replace('Input:', '').trim();
          } else if (line.includes('Output:')) {
            exampleObj.output = line.replace('Output:', '').trim();
          } else if (line.includes('Explanation:')) {
            exampleObj.explanation = line.replace('Explanation:', '').trim();
          }
        });
        
        result.examples.push(exampleObj);
      } else if (header === 'Constraints:') {
        result.constraints = content;
      } else if (header === 'Follow-up:') {
        result.followUp = content;
      }
    }
    
    return result;
  };

  const transitionToTechnical = (technicalData) => {
    setIsTransitioning(true);
    
    setTimeout(() => {
      setCurrentPhase('technical');
      setIsTransitioning(false);
      
      if (technicalData) {
        setCurrentProblem({
          title: technicalData.title,
          difficulty: technicalData.difficulty,
          description: technicalData.description,
          starter_code: technicalData.starter_code,
          function_name: technicalData.function_name
        });
        
        if (technicalData.starter_code) {
          setCode(technicalData.starter_code);
        }
      }
    }, 800);
  };

  const executeCode = async () => {
    if (!code.trim()) return;
    
    setIsExecuting(true);
    
    try {
      const response = await fetch('https://interview-ai-crdv.onrender.com/code/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          source_code: code,
          language_id: selectedLanguage,
          stdin: ""
        })
      });
      
      const result = await response.json();
      
      let outputText = '';
      let status = 'Unknown';
      
      if (result.stdout) {
        outputText = `Output:\n${result.stdout}`;
        status = result.status?.description || 'Accepted';
      } else if (result.stderr) {
        outputText = `Error:\n${result.stderr}`;
        status = result.status?.description || 'Runtime Error';
      } else if (result.compile_output) {
        outputText = `Compilation Error:\n${result.compile_output}`;
        status = 'Compilation Error';
      } else {
        outputText = 'No output received';
        status = result.status?.description || 'Unknown';
      }
      
      setOutput(outputText);
      
      await sendCodeExecutionToAI(code, outputText, status);
      
    } catch (error) {
      setOutput(`Execution failed: ${error.message}`);
    } finally {
      setIsExecuting(false);
    }
  };

  const sendCodeExecutionToAI = async (codeText, outputText, status) => {
    if (!interviewId) return;
    
    try {
      const response = await fetch(`https://interview-ai-crdv.onrender.com/interviews/${interviewId}/execute-code`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          code: codeText,
          output: outputText,
          status: status
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        addToTranscript('AI', data.feedback);
        setCurrentAIMessage(data.feedback);
        
        speakText(data.feedback);
      }
    } catch (error) {
      console.error('Error sending code execution to AI:', error);
    }
  };

  const handleEndCall = () => {
    setShowEndCallDialog(true);
  };

  const confirmEndCall = async () => {
    if (speechRecognitionRef.current) {
      speechRecognitionRef.current.stop();
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    if (speechDebounceTimerRef.current) {
      clearTimeout(speechDebounceTimerRef.current);
    }
    pendingSpeechRef.current = '';
    
    await endInterviewWithBackend();
    
    console.log('Interview ended');
    setShowEndCallDialog(false);
    
    window.location.href = '/results';
  };

  const cancelEndCall = () => {
    setShowEndCallDialog(false);
  };

  return (
    <div className="interview-container">
      <div className="header-bar">
        <div className="header-title">
          <h2>InterviewAI</h2>
          {candidateLevel && (
            <span style={{ fontSize: '0.8em', marginLeft: '10px', opacity: 0.7 }}>
              ({candidateLevel === 'intern' ? 'Intern Level' : 'New Grad Level'})
            </span>
          )}
        </div>

        <div className="header-controls">
          <button
            onClick={toggleMicrophone}
            className={`control-button ${isMicOn ? 'mic-on' : 'mic-off'}`}
          >
            {isMicOn ? <Mic size={20} /> : <MicOff size={20} />}
          </button>
          
          <button
            onClick={() => setIsCameraOn(!isCameraOn)}
            className={`control-button ${isCameraOn ? 'camera-on' : 'camera-off'}`}
          >
            {isCameraOn ? <Camera size={20} /> : <CameraOff size={20} />}
          </button>

          <button 
            onClick={handleEndCall}
            className="control-button end-call"
          >
            <Phone size={20} />
          </button>
        </div>
      </div>

      <div className="main-content">
        {currentPhase === 'behavioral' && (
          <div className={`behavioral-phase ${isTransitioning ? 'transitioning' : ''}`}>
            <div className="video-container-behavioral">
              
              <div className={`video-box-large ${isUserSpeaking ? 'speaking' : ''}`}>
                <video
                  ref={userVideoRef}
                  autoPlay
                  muted
                  className="video-element"
                />
                
                <div className="video-label">
                  <span>You</span>
                </div>
                
                {!isCameraOn && (
                  <div className="camera-off-overlay">
                    <CameraOff size={48} />
                  </div>
                )}
              </div>

              <div className={`video-box-large ${isAISpeaking ? 'speaking' : ''}`}>
                <div className="aivideo-element">
                  <img src="/aipfp.png" alt="aipfp"/>
                </div>
                
                <div className="video-label">
                  <span>Interviewer</span>
                </div>
                
                {(isAIThinking || isAISpeaking) && (
                  <div style={{ 
                    position: 'absolute', 
                    top: '10px', 
                    right: '10px',
                    background: 'rgba(0,0,0,0.6)',
                    padding: '5px 10px',
                    borderRadius: '5px',
                    fontSize: '12px',
                    color: 'white'
                  }}>
                    {isAIThinking ? 'Thinking...' : 'Speaking...'}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {currentPhase === 'technical' && (
          <div className={`technical-phase ${isTransitioning ? 'transitioning' : ''}`}>
            
            <div className="video-sidebar">
              
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
                {!isCameraOn && (
                  <div className="camera-off-overlay">
                    <CameraOff size={24} />
                  </div>
                )}
              </div>

              <div className={`video-box-small ${isAISpeaking ? 'speaking' : ''}`}>
                <div className="aivideo-element">
                  <img src="/aipfp.png" alt="aipfp"/>
                </div>
                <div className="video-label-small">
                  Interviewer
                </div>
                {isAIThinking && (
                  <div style={{ 
                    position: 'absolute', 
                    top: '5px', 
                    right: '5px',
                    background: 'rgba(0,0,0,0.6)',
                    padding: '3px 6px',
                    borderRadius: '3px',
                    fontSize: '10px',
                    color: 'white'
                  }}>
                    ...
                  </div>
                )}
              </div>
            </div>

            <div className="coding-interface">
              <div className="coding-container">
            
                <div className="problem-description">
                  {currentProblem ? (
                    <div>
                      <div className="problem-header">
                        <h3 className="problem-title">{currentProblem.title}</h3>
                        {currentProblem.difficulty && (
                          <span className={`difficulty-badge ${currentProblem.difficulty.toLowerCase()}`}>
                            {currentProblem.difficulty}
                          </span>
                        )}
                      </div>
                      
                      {(() => {
                        const parsed = parseProblemDescription(currentProblem.description);
                        return (
                          <>
                            <div className="problem-text" style={{ whiteSpace: 'pre-line', marginBottom: '20px' }}>
                              {parsed.main}
                            </div>
                            
                            {parsed.examples.length > 0 && (
                              <div className="examples-section">
                                {parsed.examples.map((example, index) => (
                                  <div key={index} className="example-item">
                                    <strong>Example {index + 1}:</strong>
                                    {example.input && <div className="example-input">Input: {example.input}</div>}
                                    {example.output && <div className="example-output">Output: {example.output}</div>}
                                    {example.explanation && <div className="example-explanation">{example.explanation}</div>}
                                  </div>
                                ))}
                              </div>
                            )}
                            
                            {parsed.constraints && (
                              <div className="constraints-section" style={{ marginTop: '15px' }}>
                                <strong>Constraints:</strong>
                                <div style={{ whiteSpace: 'pre-line', marginTop: '5px', fontSize: '0.9em' }}>
                                  {parsed.constraints}
                                </div>
                              </div>
                            )}
                            
                            {parsed.followUp && (
                              <div className="followup-section" style={{ marginTop: '15px', fontStyle: 'italic' }}>
                                <strong>Follow-up:</strong> {parsed.followUp}
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  ) : (
                    <div className="loading-text">Loading problem...</div>
                  )}
                </div>

                <div className="editor-section">
                  
                  <div className="editor-controls">
                    <select
                      value={selectedLanguage}
                      onChange={(e) => setSelectedLanguage(parseInt(e.target.value))}
                      className="language-select"
                    >
                      {languages.map((lang) => (
                        <option key={lang.id} value={lang.id}>
                          {lang.name}
                        </option>
                      ))}
                    </select>

                    <button
                      onClick={executeCode}
                      disabled={isExecuting}
                      className="run-button"
                    >
                      <Send size={16} />
                      <span>{isExecuting ? 'Running...' : 'Run Code'}</span>
                    </button>
                  </div>

                  <div className="editor-output-container">
                    
                    <div className="editor-panel">
                      <MonacoEditor
                        value={code}
                        onChange={setCode}
                        language={languages.find(l => l.id === selectedLanguage)?.monaco || 'python'}
                      />
                    </div>

                    <div className="output-panel">
                      <h4 className="output-title">Output:</h4>
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

      {showEndCallDialog && (
        <div className="dialog-overlay">
          <div className="dialog-content">
            <h3 className="dialog-title">End Interview?</h3>
            
            <p className="dialog-text">
              Are you sure you want to end the interview? Your evaluation will be generated.
            </p>
            
            <div className="dialog-buttons">
              <button
                onClick={confirmEndCall}
                className="dialog-button confirm"
              >
                Yes, End Interview
              </button>
              
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