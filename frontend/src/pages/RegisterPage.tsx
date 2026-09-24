import { AlertCircle } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";

import { AuthScene } from "../components/layout/AuthScene";
import { register as registerUser } from "../services/auth";
import type { RegisterRequest } from "../types/api";
import { extractErrorMessage } from "../utils/response";

// RegisterPage creates new user accounts for saved chat history.
export function RegisterPage() {
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    clearErrors,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterRequest>();

  async function onSubmit(values: RegisterRequest) {
    clearErrors("root");
    try {
      await registerUser(values);
      navigate("/login", {
        replace: true,
        state: { notice: "Account created successfully. You can now log in." },
      });
    } catch (error) {
      setError("root", {
        type: "server",
        message: extractErrorMessage(error),
      });
    }
  }

  return (
    <AuthScene title="Create account" subtitle="Register to save conversations and support answers.">
          <form className="space-y-4" noValidate onSubmit={handleSubmit(onSubmit)}>
            <AuthField error={errors.email?.message} label="Email">
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
            </AuthField>
            <AuthField error={errors.password?.message} label="Password">
              <input
                aria-invalid={Boolean(errors.password)}
                className={inputClass(Boolean(errors.password))}
                placeholder="Choose a password"
                type="password"
                {...register("password", {
                  required: "Password is required.",
                  maxLength: {
                    value: 128,
                    message: "Password cannot exceed 128 characters.",
                  },
                })}
              />
            </AuthField>
            <AuthField error={errors.display_name?.message} label="Display name">
              <input
                aria-invalid={Boolean(errors.display_name)}
                className={inputClass(Boolean(errors.display_name))}
                placeholder="Optional"
                {...register("display_name", {
                  maxLength: {
                    value: 120,
                    message: "Display name cannot exceed 120 characters.",
                  },
                })}
              />
            </AuthField>
            {errors.root?.message ? (
              <div aria-live="assertive" className="flex items-start gap-2 border-l-2 border-[#a95f4f] bg-[#f7e9e4]/78 px-3 py-2.5 text-sm text-[#754438]">
                <AlertCircle className="mt-0.5 shrink-0" size={16} />
                <span>{errors.root.message}</span>
              </div>
            ) : null}
            <button className="w-full rounded-full bg-[#99775c] px-4 py-3 font-semibold text-white shadow-md transition hover:bg-[#806047] disabled:cursor-not-allowed disabled:opacity-60" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Creating..." : "Create account"}
            </button>
          </form>
          <p className="mt-5 text-sm text-[#6a5546]">
            Already have an account? <Link className="font-semibold text-[#99775c]" to="/login">Login</Link>
          </p>
    </AuthScene>
  );
}

function AuthField({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold text-[#604b3e]">{label}</span>
      {children}
      {error ? <span className="mt-1.5 block text-xs text-[#974f40]">{error}</span> : null}
    </label>
  );
}

function inputClass(invalid: boolean): string {
  return `w-full rounded-xl border bg-[#f7f4ee]/80 px-4 py-3 text-[#3f3028] outline-none transition placeholder:text-[#8c7869] focus:ring-2 ${
    invalid
      ? "border-[#a95f4f]/65 focus:border-[#a95f4f] focus:ring-[#a95f4f]/12"
      : "border-[#99775c]/25 focus:border-[#99775c] focus:ring-[#99775c]/15"
  }`;
}
