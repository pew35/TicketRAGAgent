import { Link } from "react-router-dom";

// MarketingNav is the public homepage navigation bar.
export function MarketingNav() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 flex w-full items-center justify-between border-b border-white/35 bg-[#eae7dd]/55 px-5 py-4 backdrop-blur-xl sm:px-8 lg:px-10">
      <Link to="/" className="display-font text-xl font-semibold text-[#3f3028]">
        Ticket RAG Agent
      </Link>
      <nav className="flex items-center gap-3">
        <Link className="rounded-full px-3 py-2 text-sm font-semibold text-[#644a38] hover:text-[#3f3028]" to="/login">
          Login
        </Link>
        <Link className="rounded-full bg-[#99775c] px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#806047]" to="/register">
          Register
        </Link>
      </nav>
    </header>
  );
}
