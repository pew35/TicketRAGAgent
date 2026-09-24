// SupportAgentScene shows the reusable support representative and speech bubble.
type SupportAgentSceneProps = {
  message: string;
  compact?: boolean;
  className?: string;
  showBubble?: boolean;
};

export function SupportAgentScene({ message, compact = false, className = "" }: SupportAgentSceneProps) {
  return (
    <div
      className={`relative overflow-hidden rounded-lg border border-line bg-cover bg-center shadow-sm ${compact ? "min-h-80" : "min-h-[560px]"} ${className}`}
      style={{ backgroundImage: `url('${import.meta.env.BASE_URL}assets/support-office-bg.png')` }}
    >
      <div className="absolute inset-0 bg-gradient-to-r from-black/10 via-white/5 to-white/25" />
      <img
        alt="Customer support representative"
        className={
          compact
            ? "absolute bottom-0 left-2 h-[78%] max-w-[58%] object-contain object-bottom"
            : "absolute bottom-0 left-0 h-[82%] max-w-[52%] object-contain object-bottom"
        }
        src={`${import.meta.env.BASE_URL}assets/support-agent-character.png`}
      />
      <div
        className={
          compact
            ? "absolute right-4 top-5 w-[58%] rounded-lg border border-white/50 bg-white/70 p-4 shadow-lg backdrop-blur-md"
            : "absolute right-8 top-1/2 w-[48%] -translate-y-1/2 rounded-lg border border-white/50 bg-white/68 p-6 shadow-xl backdrop-blur-md"
        }
      >
        <div className="absolute left-[-10px] top-12 h-5 w-5 rotate-45 border-b border-l border-white/50 bg-white/70 backdrop-blur-md" />
        <p className={compact ? "relative text-sm font-semibold leading-6 text-ink" : "relative text-xl font-semibold leading-8 text-ink"}>
          {message}
        </p>
      </div>
    </div>
  );
}

// SupportAgentForeground composes the separate foreground layer and dialogue bubble.
export function SupportAgentForeground({ message, compact = false, className = "", showBubble = true }: SupportAgentSceneProps) {
  return (
    <div className={`pointer-events-none relative overflow-visible ${compact ? "min-h-[420px]" : "min-h-screen"} ${className}`}>
      <div className="agent-loop absolute inset-x-0 bottom-0">
        <img
          alt="Customer support agent at desk"
          className={
            compact
              ? "block w-full object-contain object-bottom drop-shadow-2xl"
              : "block w-full max-w-none object-contain object-bottom drop-shadow-2xl"
          }
          src={`${import.meta.env.BASE_URL}assets/support-agent-foreground.png`}
        />
      </div>
      <div className="agent-light-sweep absolute bottom-[6%] left-[4%] h-[18%] w-[88%] rounded-full bg-white/25 blur-2xl" />
      {showBubble ? (
        <div
          className={
            compact
              ? "pointer-events-auto absolute right-4 top-8 w-[56%] rounded-lg border border-white/55 bg-white/72 p-4 shadow-xl backdrop-blur-md"
              : "pointer-events-auto absolute left-[12%] top-[10%] w-[72%] rounded-lg border border-white/55 bg-white/72 p-6 shadow-2xl backdrop-blur-md"
          }
        >
          <div className="absolute bottom-[-10px] left-14 h-5 w-5 rotate-45 border-b border-r border-white/55 bg-white/68" />
          <p className={compact ? "text-sm font-semibold leading-6 text-ink" : "text-lg font-semibold leading-8 text-ink"}>
            {message}
          </p>
        </div>
      ) : null}
    </div>
  );
}
