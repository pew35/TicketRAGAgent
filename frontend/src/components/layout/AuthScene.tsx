import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

import { PortfolioDeskStage } from "../agent/PortfolioDeskStage";
import { SceneBackground } from "./SceneBackground";

type AuthSceneProps = {
  title: string;
  subtitle: string;
  children: React.ReactNode;
};

// AuthScene provides the shared fixed desk environment for login and registration.
export function AuthScene({ title, subtitle, children }: AuthSceneProps) {
  return (
    <main className="relative min-h-screen overflow-x-hidden bg-[#eae7dd] text-[#3f3028]">
      <SceneBackground />
      <PortfolioDeskStage />
      <Link
        className="fixed left-5 top-5 z-40 inline-flex items-center gap-2 rounded-full border border-white/45 bg-[#eae7dd]/72 px-4 py-2 text-sm font-semibold text-[#644a38] shadow-sm backdrop-blur-xl transition hover:bg-[#f7f4ee] sm:left-8"
        to="/"
      >
        <ArrowLeft aria-hidden="true" size={16} />
        Home
      </Link>
      <section className="relative z-30 ml-auto flex min-h-screen w-full items-start justify-center px-5 pb-[48vw] pt-24 sm:px-8 lg:w-[54%] lg:px-10 lg:pb-[31vh] lg:pt-28 xl:w-[50%]">
        <div className="w-full max-w-md rounded-[24px] border border-white/55 bg-[#eae7dd]/82 p-7 shadow-[0_24px_70px_rgba(83,57,40,0.2)] backdrop-blur-xl sm:p-9">
          <p className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-[#99775c]">
            Ticket RAG Agent
          </p>
          <h1 className="display-font text-4xl font-semibold leading-none text-[#3f3028]">{title}</h1>
          <p className="mb-7 mt-3 text-sm leading-6 text-[#6a5546]">{subtitle}</p>
          {children}
        </div>
      </section>
    </main>
  );
}
