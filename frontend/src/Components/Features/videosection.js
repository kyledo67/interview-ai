import React, { useEffect, useRef } from 'react';
import './VideoSection.css';

export default function VideoSection() {
  const videoRef = useRef(null);
  const observerRef = useRef(null);

  const looptime = 2;
  const resetscroll = 0.25;

  useEffect(() => {
    const video = videoRef.current;

    const handleTimeUpdate = () => {
      if (video.duration - video.currentTime < 0.1) {
        video.currentTime = looptime;
        video.play();
      }
    };
    video.addEventListener('timeupdate', handleTimeUpdate);

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry.isIntersecting && entry.boundingClientRect.top > 0) {
          video.currentTime = 0;
        }
      },
      { threshold: resetscroll }
    );
    observerRef.current.observe(video);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      if (observerRef.current) observerRef.current.disconnect();
    };
  }, []);

  return (
    <div className="video-section">
      <video
        ref={videoRef}
        src="/vid.MP4"
        muted
        autoPlay
        playsInline
        preload="auto"
        className="video-player"
      />
    </div>
  );
}