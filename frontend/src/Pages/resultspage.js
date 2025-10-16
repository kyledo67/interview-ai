import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trophy, TrendingUp, AlertCircle, CheckCircle, Home } from 'lucide-react';
import './resultspage.css';

const ResultsPage = () => {
  const navigate = useNavigate();
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const evalData = localStorage.getItem('lastInterviewEvaluation');
    
    if (evalData) {
      try {
        const parsed = JSON.parse(evalData);
        setEvaluation(parsed);
      } catch (error) {
        console.error('Failed to parse evaluation:', error);
      }
    }
    
    setLoading(false);
  }, []);

  const getScoreColor = (score) => {
    if (score >= 8) return '#22c55e'; // green
    if (score >= 6) return '#eab308'; // yellow
    if (score >= 4) return '#f97316'; // orange
    return '#ef4444'; // red
  };

  const getRecommendationStyle = (recommendation) => {
    if (recommendation === 'Strong Hire') return { color: '#22c55e', icon: <CheckCircle size={24} /> };
    if (recommendation === 'Hire') return { color: '#84cc16', icon: <CheckCircle size={24} /> };
    if (recommendation === 'No Hire') return { color: '#f97316', icon: <AlertCircle size={24} /> };
    return { color: '#ef4444', icon: <AlertCircle size={24} /> };
  };

  const handleReturnHome = () => {
    localStorage.removeItem('lastInterviewEvaluation');
    navigate('/');
  };

  if (loading) {
    return (
      <div className="results-container">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading your results...</p>
        </div>
      </div>
    );
  }

  if (!evaluation) {
    return (
      <div className="results-container">
        <div className="error-state">
          <AlertCircle size={48} color="#ef4444" />
          <h2>No Results Found</h2>
          <p>We couldn't find your interview results. Please complete an interview first.</p>
          <button onClick={handleReturnHome} className="home-button">
            <Home size={20} />
            Return Home
          </button>
        </div>
      </div>
    );
  }

  const recStyle = getRecommendationStyle(evaluation.recommendation);

  return (
    <div className="results-container">
      <div className="results-content">
        
        {/* Header */}
        <div className="results-header">
          <Trophy size={48} color="#3b82f6" />
          <h1>Interview Results</h1>
          <p className="results-subtitle">Here's how you performed</p>
        </div>

        {/* Scores Section */}
        <div className="scores-grid">
          <div className="score-card">
            <div className="score-label">Behavioral</div>
            <div className="score-circle" style={{ borderColor: getScoreColor(evaluation.behavioral_score) }}>
              <span className="score-value" style={{ color: getScoreColor(evaluation.behavioral_score) }}>
                {evaluation.behavioral_score}
              </span>
              <span className="score-max">/10</span>
            </div>
          </div>

          <div className="score-card main-score">
            <div className="score-label">Overall Score</div>
            <div className="score-circle large" style={{ borderColor: getScoreColor(evaluation.overall_score) }}>
              <span className="score-value" style={{ color: getScoreColor(evaluation.overall_score) }}>
                {evaluation.overall_score}
              </span>
              <span className="score-max">/10</span>
            </div>
          </div>

          <div className="score-card">
            <div className="score-label">Technical</div>
            <div className="score-circle" style={{ borderColor: getScoreColor(evaluation.technical_score) }}>
              <span className="score-value" style={{ color: getScoreColor(evaluation.technical_score) }}>
                {evaluation.technical_score}
              </span>
              <span className="score-max">/10</span>
            </div>
          </div>
        </div>

        {/* Recommendation Badge */}
        <div className="recommendation-section">
          <div className="recommendation-badge" style={{ borderColor: recStyle.color }}>
            {recStyle.icon}
            <span style={{ color: recStyle.color }}>{evaluation.recommendation}</span>
          </div>
        </div>

        {/* Detailed Feedback */}
        <div className="feedback-section">
          <h2>Detailed Feedback</h2>
          <p className="feedback-text">{evaluation.detailed_feedback}</p>
        </div>

        {/* Strengths and Improvements */}
        <div className="strengths-improvements-grid">
          <div className="feedback-card strengths-card">
            <div className="feedback-card-header">
              <TrendingUp size={24} color="#22c55e" />
              <h3>Strengths</h3>
            </div>
            <ul className="feedback-list">
              {evaluation.strengths.map((strength, index) => (
                <li key={index}>
                  <CheckCircle size={16} color="#22c55e" />
                  <span>{strength}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="feedback-card improvements-card">
            <div className="feedback-card-header">
              <AlertCircle size={24} color="#f97316" />
              <h3>Areas to Improve</h3>
            </div>
            <ul className="feedback-list">
              {evaluation.improvements.map((improvement, index) => (
                <li key={index}>
                  <AlertCircle size={16} color="#f97316" />
                  <span>{improvement}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Actions */}
        <div className="results-actions">
          <button onClick={handleReturnHome} className="action-button primary">
            <Home size={20} />
            Return Home
          </button>
        </div>
      </div>
    </div>
  );
};

export default ResultsPage;