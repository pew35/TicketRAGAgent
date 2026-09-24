import { Code2 } from "lucide-react";

import { portfolio } from "../../config/portfolio";

type PortfolioDeskStageProps = {
  showPortfolio?: boolean;
};

// PortfolioDeskStage keeps the beaver and desk fixed while page content scrolls above it.
export function PortfolioDeskStage({ showPortfolio = true }: PortfolioDeskStageProps) {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-x-0 bottom-0 z-10 overflow-hidden">
      <div className="relative -left-[4vw] w-[180vw] lg:left-[1vw] lg:w-[96vw] lg:max-w-[1900px]">
        <img
          alt=""
          className="agent-loop block h-auto w-full select-none object-contain object-bottom"
          src={`${import.meta.env.BASE_URL}assets/support-agent-desk-v5-transparent.png`}
        />
        {showPortfolio ? (
          <div className="portfolio-sign pointer-events-auto absolute bottom-[27%] left-[48%] right-[8%] hidden items-center justify-between gap-6 text-[#3f3028] lg:flex">
            <div className="min-w-0">
              <p className="display-font truncate text-2xl font-semibold leading-none xl:text-3xl">
                {portfolio.owner}
              </p>
              <p className="mt-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#795b46]">
                Ticket RAG Agent · {portfolio.projectLabel}
              </p>
            </div>
            <div className="flex max-w-[58%] flex-wrap justify-end gap-x-3 gap-y-1.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-[#644a38] xl:text-[11px]">
              <Code2 aria-hidden="true" className="text-[#99775c]" size={15} />
              {portfolio.technologies.map((technology) => (
                <span key={technology}>{technology}</span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
