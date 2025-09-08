import React from "react";
import Header from "../Components/Header/header";
import Hero from "../Components/Hero/hero";
import { Features, Feedback } from "../Components/Features/features";
import VideoSection from "../Components/Features/videosection";

export default function LandingPage() {
  return (
    <>
      {/*header on top*/}
      <Header />

      {/*main page*/}
      <main className="page">
        <section>
          <Hero />
        </section>

        <VideoSection />

        <Features />

        <section>
          <Feedback />
        </section>
      </main>
    </>
  );
}