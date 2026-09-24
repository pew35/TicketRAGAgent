import { AlertCircle, CheckCircle2 } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";

import { AuthScene } from "../components/layout/AuthScene";
import { login } from "../services/auth";
import type { LoginRequest } from "../types/api";
import { extractErrorMessage } from "../utils/response";

type LoginLocationState = {
  notice?: string;
};

// LoginPage authenticates existing users before opening the chat app.
export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const notice = (location.state as LoginLocationState | null)?.notice;
  const {
    register,
    handleSubmit,
    clearErrors,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginRequest>();

  async function onSubmit(values: LoginRequest) {
    clearErrors("root");
    try {
      await login(values);
      navigate("/app", { replace: true });
    } catch (error) {
      setError("root", {
        type: "server",
        message: extractErrorMessage(error),
      });
    }
  }

  return (
    <AuthScene title="Welcome back" subtitle="Login to continue your support conversations.">
      {notice ? (
        <div aria-live="polite" className="mb-4 flex items-start gap-2 border-l-2 border-[#54766b] bg-[#e5efea]/76 px-3 py-2.5 text-sm text-[#38584f]">
          <CheckCircle2 className="mt-0.5 shrink-0" size={16} />
          <span>{notice}</span>
        </div>
      ) : null}
      <form className="space-y-4" noValidate onSubmit={handleSubmit(onSubmit)}>
        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold text-[#604b3e]">Email</span>
          <input
            aria-invalid={Boolean(errors.email)}
            className={inputClass(Boolean(errors.email))}
            placeholder="you@example.com"
            type="email"
            {...register("email", {
              required: "Email is required.",
              pattern: {
                value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                message: "Enter a valid email address.",
              },
            })}
          />
          {errors.email?.message ? <span className="mt-1.5 block text-xs text-[#974f40]">{errors.email.message}</span> : null}
        </label>
        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold text-[#604b3e]">Password</span>
          <input
            aria-invalid={Boolean(errors.password)}
            className={inputClass(Boolean(errors.password))}
            placeholder="Password"
            type="password"
            {...register("password", { required: "Password is required." })}
          />
          {errors.password?.message ? <span className="mt-1.5 block text-xs text-[#974f40]">{errors.password.message}</span> : null}
        </label>
        {errors.root?.message ? (
          <div aria-live="assertive" className="flex items-start gap-2 border-l-2 border-[#a95f4f] bg-[#f7e9e4]/78 px-3 py-2.5 text-sm text-[#754438]">
            <AlertCircle className="mt-0.5 shrink-0" size={16} />
            <span>{errors.root.message}</span>
          </div>
        ) : null}
        <button className="w-full rounded-full bg-[#99775c] px-4 py-3 font-semibold text-white shadow-md transition hover:bg-[#806047] disabled:cursor-not-allowed disabled:opacity-60" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Logging in..." : "Login"}
        </button>
      </form>
      <p className="mt-5 text-sm text-[#6a5546]">
        New here? <Link className="font-semibold text-[#99775c]" to="/register">Create an account</Link>
      </p>
    </AuthScene>
  );
}

function inputClass(invalid: boolean): string {
  return `w-full rounded-xl border bg-[#f7f4ee]/80 px-4 py-3 text-[#3f3028] outline-none transition placeholder:text-[#8c7869] focus:ring-2 ${
    invalid
      ? "border-[#a95f4f]/65 focus:border-[#a95f4f] focus:ring-[#a95f4f]/12"
      : "border-[#99775c]/25 focus:border-[#99775c] focus:ring-[#99775c]/15"
  }`;
}
