import { TicketCheck } from "lucide-react";

type SceneBackgroundProps = {
  className?: string;
};

// SceneBackground softens the office artwork so foreground content remains dominant.
export function SceneBackground({ className = "" }: SceneBackgroundProps) {
  return (
    <div aria-hidden="true" className={`pointer-events-none fixed inset-0 z-0 overflow-hidden ${className}`}>
      <div
        className="scene-background-image absolute -inset-[2%] bg-cover bg-center"
        style={{ backgroundImage: `url('${import.meta.env.BASE_URL}assets/support-office-bg-clean.png')` }}
      />
      <div className="scene-background-wash absolute inset-0" />
      <div className="absolute inset-0 bg-[#eae7dd]/16 backdrop-blur-[1.5px]" />
      <div className="scene-wall-brand absolute left-[31%] top-[19%] hidden items-center gap-3 text-[#594335] lg:flex">
        <span className="flex h-14 w-14 items-center justify-center rounded-[18px] border border-[#99775c]/35 bg-[#eae7dd]/58 shadow-[0_10px_30px_rgba(83,57,40,0.12)] backdrop-blur-md">
          <TicketCheck strokeWidth={1.65} size={27} />
        </span>
        <span>
          <span className="display-font block text-2xl font-semibold leading-none">Ticket RAG</span>
          <span className="mt-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-[#99775c]">
            Support Intelligence
          </span>
        </span>
      </div>
    </div>
  );
}
