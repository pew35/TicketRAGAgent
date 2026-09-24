// ChatAgentStage keeps the beaver in its own column so the sidebar never covers it.
export function ChatAgentStage() {
  return (
    <aside className="pointer-events-none relative z-40 hidden h-full w-[clamp(270px,26vw,390px)] shrink-0 overflow-visible bg-transparent lg:block">
      <img
        alt="Beaver customer support agent working at the front desk"
        className="agent-loop absolute -left-[18px] bottom-0 w-[1300px] max-w-none select-none object-contain object-left-bottom drop-shadow-2xl"
        src={`${import.meta.env.BASE_URL}assets/support-agent-desk-v5-transparent.png`}
      />
    </aside>
  );
}
