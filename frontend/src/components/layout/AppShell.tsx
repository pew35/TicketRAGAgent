// AppShell owns the main authenticated page frame.
export function AppShell({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-surface text-ink">{children}</div>;
}
