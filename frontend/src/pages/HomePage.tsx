import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BadgeCheck, Clock3, SearchCheck } from "lucide-react";

import { PortfolioDeskStage } from "../components/agent/PortfolioDeskStage";
import { MarketingNav } from "../components/layout/MarketingNav";
import { SceneBackground } from "../components/layout/SceneBackground";

const storySections = [
  {
    eyebrow: "Built for support teams",
    title: "Ticket RAG Agent",
    body: "A RAG-based assistant that turns historical service tickets into fast, reliable guidance for customer support teams.",
    detail: "Find proven answers without searching old cases by hand.",
    icon: SearchCheck,
  },
  {
    eyebrow: "Faster answers",
    title: "Find proven solutions faster",
    body: "Ask a customer question in natural language and retrieve the most relevant resolutions from your support knowledge base.",
    detail: "Spend less time searching and more time solving.",
    icon: Clock3,
  },
  {
    eyebrow: "Consistent quality",
    title: "Keep every answer consistent",
    body: "Reuse grounded solutions from similar cases so customers receive clear, dependable service across every conversation.",
    detail: "Turn past support work into repeatable service quality.",
    icon: BadgeCheck,
  },
];

// HomePage presents one full-screen product chapter at a time above the fixed desk scene.
export function HomePage() {
  const [activeSection, setActiveSection] = useState(0);
  const sectionRefs = useRef<Array<HTMLElement | null>>([]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntry = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

        if (visibleEntry) {
          setActiveSection(Number(visibleEntry.target.getAttribute("data-index")));
        }
      },
      { rootMargin: "-28% 0px -28% 0px", threshold: [0.2, 0.5, 0.75] },
    );

    sectionRefs.current.forEach((section) => section && observer.observe(section));
    return () => observer.disconnect();
  }, []);

  return (
    <main className="home-scroll relative h-screen snap-y snap-mandatory overflow-x-hidden overflow-y-auto bg-[#eae7dd] text-[#3f3028]">
      <SceneBackground />
      <MarketingNav />
      <PortfolioDeskStage />

      <div className="relative z-20 ml-auto w-full lg:w-[54%] xl:w-[52%]">
        {storySections.map((section, index) => {
          const Icon = section.icon;
          const positionClass =
            index === activeSection
              ? "translate-y-0 scale-100 opacity-100 blur-0"
              : index < activeSection
                ? "-translate-y-10 scale-[0.94] opacity-25 blur-[2px]"
                : "translate-y-10 scale-[0.94] opacity-25 blur-[2px]";

          return (
            <article
              className="flex min-h-screen snap-start items-center px-5 pb-[48vw] pt-24 sm:px-8 lg:px-10 lg:pb-[34vh] lg:pt-28 xl:px-14"
              data-index={index}
              key={section.title}
              ref={(node) => {
                sectionRefs.current[index] = node;
              }}
            >
              <div
                className={`home-story-card w-full max-w-2xl rounded-[24px] border border-white/55 bg-[#eae7dd]/78 p-7 shadow-[0_24px_70px_rgba(83,57,40,0.18)] backdrop-blur-xl transition-all duration-700 ease-out sm:p-9 ${positionClass}`}
              >
                <div className="mb-6 flex items-center justify-between gap-4">
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#99775c]">
                    {section.eyebrow}
                  </p>
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[#99775c]/25 bg-[#f7f4ee]/75 text-[#99775c]">
                    <Icon aria-hidden="true" size={19} />
                  </span>
                </div>
                <h1 className="display-font max-w-2xl text-4xl font-semibold leading-[1.02] text-[#3f3028] sm:text-5xl xl:text-6xl">
                  {section.title}
                </h1>
                <p className="mt-5 max-w-xl text-base leading-7 text-[#5e4b3e] sm:text-lg sm:leading-8">
                  {section.body}
                </p>
                <div className="mt-7 border-t border-[#99775c]/20 pt-5 text-sm font-semibold text-[#765a46]">
                  {section.detail}
                </div>
                {index === 0 ? <HeroActions /> : null}
              </div>
            </article>
          );
        })}
      </div>

      <div className="fixed right-4 top-1/2 z-40 hidden -translate-y-1/2 flex-col gap-3 lg:flex">
        {storySections.map((section, index) => (
          <button
            aria-label={`Go to ${section.title}`}
            className={`h-2.5 rounded-full bg-[#99775c] transition-all duration-300 ${index === activeSection ? "w-7" : "w-2.5 opacity-35"}`}
            key={section.title}
            onClick={() => sectionRefs.current[index]?.scrollIntoView({ behavior: "smooth" })}
            type="button"
          />
        ))}
      </div>
    </main>
  );
}

function HeroActions() {
  return (
    <div className="mt-8 flex flex-wrap gap-3">
      <Link
        className="inline-flex items-center gap-2 rounded-full bg-[#99775c] px-5 py-3 text-sm font-semibold text-white shadow-md transition hover:-translate-y-0.5 hover:bg-[#806047]"
        to="/app"
      >
        Start Chat
        <ArrowRight size={17} />
      </Link>
      <Link
        className="rounded-full border border-[#99775c]/30 bg-[#f7f4ee]/65 px-5 py-3 text-sm font-semibold text-[#533d2f] transition hover:bg-[#f7f4ee]"
        to="/login"
      >
        Login
      </Link>
      <Link
        className="rounded-full border border-[#99775c]/30 bg-transparent px-5 py-3 text-sm font-semibold text-[#533d2f] transition hover:bg-[#f7f4ee]/65"
        to="/register"
      >
        Register
      </Link>
    </div>
  );
}
