import { ArrowUpRight } from "lucide-react";

export function OAuthButton({ register }: { register: boolean }) {
  return (
    <a className="google-button" href="/api/v1/auth/google/start">
      <span className="google-mark" aria-hidden="true">
        G
      </span>
      <span>{register ? "Sign up with Google" : "Continue with Google"}</span>
      <ArrowUpRight size={16} aria-hidden="true" />
    </a>
  );
}
